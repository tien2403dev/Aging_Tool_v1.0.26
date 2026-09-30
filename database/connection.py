import sqlite3
from pathlib import Path
from typing import Union


DEFAULT_BUSY_TIMEOUT_MS = 60_000


def create_connection(
    database_path: Union[str, Path],
    busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
) -> sqlite3.Connection:
    """
    Tạo một SQLite connection mới.

    Mỗi thread phải tự tạo connection riêng.
    Không chia sẻ connection giữa UI thread và worker thread.
    """

    if busy_timeout_ms < 0:
        raise ValueError("busy_timeout_ms không được nhỏ hơn 0")

    database_path = Path(database_path)

    # Tự tạo thư mục chứa database nếu chưa tồn tại.
    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        str(database_path),
        timeout=busy_timeout_ms / 1000,
    )

    try:
        connection.row_factory = sqlite3.Row

        # Bắt buộc bật để ON DELETE CASCADE hoạt động.
        connection.execute("PRAGMA foreign_keys = ON")

        # Không sử dụng WAL vì database sẽ đặt trên ổ mạng.
        connection.execute("PRAGMA journal_mode = DELETE")

        # Ưu tiên an toàn dữ liệu.
        connection.execute("PRAGMA synchronous = FULL")

        # Đợi tối đa 60 giây nếu database đang bị lock.
        connection.execute(
            f"PRAGMA busy_timeout = {busy_timeout_ms}"
        )

        return connection

    except Exception:
        connection.close()
        raise