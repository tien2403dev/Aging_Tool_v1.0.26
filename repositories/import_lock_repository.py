from __future__ import annotations

import getpass
import os
import socket
import uuid

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Union

from database.connection import create_connection


LOCK_NAME = "GLOBAL_IMPORT_LOCK"

# Import file lớn có thể mất thời gian.
# Worker sau này sẽ cập nhật heartbeat định kỳ.
LOCK_TIMEOUT_MINUTES = 15


@dataclass
class LockInfo:
    batch_id: str
    import_type: str
    file_name: str
    machine_name: str
    windows_user: str
    process_id: int
    acquired_at: str
    heartbeat_at: str
    expires_at: str


class ImportInProgressError(Exception):
    """Được raise khi một máy khác đang giữ import lock."""

    def __init__(self, lock_info: LockInfo):
        self.lock_info = lock_info

        message = (
            "Một máy khác đang thực hiện import.\n\n"
            f"Loại dữ liệu: {lock_info.import_type}\n"
            f"Máy thực hiện: {lock_info.machine_name}\n"
            f"Người dùng: {lock_info.windows_user}\n"
            f"File: {lock_info.file_name}\n"
            f"Thời gian bắt đầu: {lock_info.acquired_at}"
        )

        super().__init__(message)


class ImportLockRepository:
    def __init__(self, database_path: Union[str, Path]):
        self.database_path = database_path

    def acquire_lock(
        self,
        import_type: str,
        file_name: str,
    ) -> LockInfo:
        """
        Chiếm global import lock.

        Nếu lock đang được máy khác giữ và chưa hết hạn,
        raise ImportInProgressError.
        """

        import_type = import_type.upper().strip()

        if import_type not in ("PRIME", "CUM"):
            raise ValueError("import_type chỉ được là PRIME hoặc CUM")

        now = datetime.now()
        expires_at = now + timedelta(
            minutes=LOCK_TIMEOUT_MINUTES
        )

        batch_id = str(uuid.uuid4())

        new_lock = LockInfo(
            batch_id=batch_id,
            import_type=import_type,
            file_name=file_name,
            machine_name=socket.gethostname(),
            windows_user=getpass.getuser(),
            process_id=os.getpid(),
            acquired_at=now.strftime("%Y-%m-%d %H:%M:%S"),
            heartbeat_at=now.strftime("%Y-%m-%d %H:%M:%S"),
            expires_at=expires_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

        connection = create_connection(self.database_path)

        try:
            # Đảm bảo hai máy không cùng kiểm tra và cùng tạo lock.
            connection.execute("BEGIN IMMEDIATE")

            row = connection.execute(
                """
                SELECT
                    batch_id,
                    import_type,
                    file_name,
                    machine_name,
                    windows_user,
                    process_id,
                    acquired_at,
                    heartbeat_at,
                    expires_at
                FROM import_lock
                WHERE lock_name = ?
                """,
                (LOCK_NAME,),
            ).fetchone()

            if row is not None:
                current_lock = LockInfo(
                    batch_id=row["batch_id"],
                    import_type=row["import_type"],
                    file_name=row["file_name"],
                    machine_name=row["machine_name"],
                    windows_user=row["windows_user"],
                    process_id=row["process_id"],
                    acquired_at=row["acquired_at"],
                    heartbeat_at=row["heartbeat_at"],
                    expires_at=row["expires_at"],
                )

                if not self._is_expired(current_lock.expires_at):
                    connection.rollback()
                    raise ImportInProgressError(current_lock)

                # Lock cũ đã hết hạn, thường do app bị crash hoặc mất mạng.
                connection.execute(
                    """
                    DELETE FROM import_lock
                    WHERE lock_name = ?
                    """,
                    (LOCK_NAME,),
                )

            connection.execute(
                """
                INSERT INTO import_lock (
                    lock_name,
                    batch_id,
                    import_type,
                    file_name,
                    machine_name,
                    windows_user,
                    process_id,
                    acquired_at,
                    heartbeat_at,
                    expires_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    LOCK_NAME,
                    new_lock.batch_id,
                    new_lock.import_type,
                    new_lock.file_name,
                    new_lock.machine_name,
                    new_lock.windows_user,
                    new_lock.process_id,
                    new_lock.acquired_at,
                    new_lock.heartbeat_at,
                    new_lock.expires_at,
                ),
            )

            connection.commit()

            return new_lock

        except Exception:
            if connection.in_transaction:
                connection.rollback()

            raise

        finally:
            connection.close()

    def refresh_heartbeat(
        self,
        batch_id: str,
    ) -> bool:
        """
        Gia hạn lock trong lúc đang import.
        Sau này worker sẽ gọi định kỳ.
        """

        now = datetime.now()
        expires_at = now + timedelta(
            minutes=LOCK_TIMEOUT_MINUTES
        )

        connection = create_connection(self.database_path)

        try:
            cursor = connection.execute(
                """
                UPDATE import_lock
                SET
                    heartbeat_at = ?,
                    expires_at = ?
                WHERE
                    lock_name = ?
                    AND batch_id = ?
                """,
                (
                    now.strftime("%Y-%m-%d %H:%M:%S"),
                    expires_at.strftime("%Y-%m-%d %H:%M:%S"),
                    LOCK_NAME,
                    batch_id,
                ),
            )

            connection.commit()

            return cursor.rowcount == 1

        finally:
            connection.close()

    def release_lock(
        self,
        batch_id: str,
    ) -> None:
        """
        Chỉ máy đang giữ đúng batch_id mới được xóa lock.
        """

        connection = create_connection(self.database_path)

        try:
            connection.execute(
                """
                DELETE FROM import_lock
                WHERE
                    lock_name = ?
                    AND batch_id = ?
                """,
                (
                    LOCK_NAME,
                    batch_id,
                ),
            )

            connection.commit()

        finally:
            connection.close()

    @staticmethod
    def _is_expired(expires_at: str) -> bool:
        """
        Lock chỉ được coi là hết hạn khi parse được thời gian
        và thời gian hết hạn đã qua.
        """

        try:
            expires_datetime = datetime.strptime(
                expires_at,
                "%Y-%m-%d %H:%M:%S",
            )

        except ValueError:
            # Không tự xóa lock có dữ liệu thời gian bất thường.
            return False

        return expires_datetime <= datetime.now()