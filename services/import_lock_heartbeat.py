from __future__ import annotations

import threading

from repositories.import_lock_repository import (
    ImportLockRepository,
)


HEARTBEAT_INTERVAL_SECONDS = 60


class ImportLockHeartbeat:
    """
    Gia hạn import lock định kỳ trong lúc đang import.

    Chạy ở thread nền riêng để quá trình đọc Excel lớn
    không làm lock bị hết hạn.
    """

    def __init__(
        self,
        lock_repository: ImportLockRepository,
        batch_id: str,
    ):
        self.lock_repository = lock_repository
        self.batch_id = batch_id

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return

        self._thread = threading.Thread(
            target=self._run,
            name="ImportLockHeartbeat",
            daemon=True,
        )

        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop_event.wait(
            HEARTBEAT_INTERVAL_SECONDS
        ):
            is_refreshed = (
                self.lock_repository.refresh_heartbeat(
                    self.batch_id
                )
            )

            # Lock không còn thuộc batch hiện tại.
            # Dừng thread, không tiếp tục update.
            if not is_refreshed:
                return