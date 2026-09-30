import os
import sys
import traceback

from pathlib import Path

from PyQt5.QtWidgets import (
    QMessageBox,
)
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
from database.schema import initialize_database
from ui.main_window import MainWindow


PROJECT_ROOT = Path(__file__).resolve().parent


def _global_exception_handler(exc_type, exc_value, exc_traceback) -> None:
    """
    Bắt exception chưa được xử lý trong Qt/PyQt.

    Đặc biệt quan trọng khi chạy bản EXE -- không để một exception
    trong callback/signal làm PGM tự đóng mà không có thông báo.
    """
    try:
        log_root = (
            Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
            / "Aging_Yield"
            / "logs"
        )
        log_root.mkdir(parents=True, exist_ok=True)
        log_path = log_root / "pgm_runtime_error.log"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write("\n" + "=" * 80 + "\n")
            handle.write(traceback.format_exc())
    except BaseException:
        pass

    try:
        message = "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        ).strip()
        QMessageBox.critical(
            None,
            "Lỗi Aging Yield",
            "Đã xảy ra lỗi trong chương trình. PGM vẫn được giữ mở.\n\n"
            + (message[-6000:] if message else str(exc_value)),
        )
    except BaseException:
        pass


def get_database_path() -> Path:
    """
    Lấy database do Launcher truyền vào.

    Chỉ cho phép database chưa tồn tại
    trong lần khởi tạo đầu tiên.
    """

    configured_path = os.environ.get(
        "AGING_DB_PATH"
    )

    if configured_path:
        database_path = Path(
            configured_path
        )

        allow_database_creation = (
            os.environ.get(
                "AGING_ALLOW_DB_CREATE"
            )
            == "1"
        )

        if (
            not database_path.is_file()
            and not allow_database_creation
        ):
            raise FileNotFoundError(
                "Không tìm thấy database dùng chung:\n"
                f"{database_path}\n\n"
                "Vui lòng kiểm tra kết nối mạng."
            )

        return database_path

    if getattr(
        sys,
        "frozen",
        False,
    ):
        raise RuntimeError(
            "Chưa nhận được đường dẫn database.\n\n"
            "Vui lòng mở Aging Yield bằng "
            "Aging Yield Launcher."
        )

    return (
        PROJECT_ROOT
        / "database"
        / "aging_monitoring.db"
    )
def complete_database_initialization(
    database_path: Path,
) -> None:
    """
    Xóa trạng thái initializing sau khi
    initialize_database thành công.
    """

    if (
        os.environ.get(
            "AGING_ALLOW_DB_CREATE"
        )
        != "1"
    ):
        return

    initializing_flag = (
        database_path.parent
        / "database_initializing.flag"
    )

    if initializing_flag.is_file():
        initializing_flag.unlink()

def main() -> None:
    """
    Khởi tạo ứng dụng và hiển thị lỗi
    database rõ ràng nếu có.
    """

    sys.excepthook = _global_exception_handler

    app = QApplication(sys.argv)

    try:
        database_path = (
            get_database_path()
        )

        initialize_database(
            database_path
        )

        complete_database_initialization(
            database_path
        )

    except Exception as error:
        QMessageBox.critical(
            None,
            "Không thể mở Aging Yield",
            str(error),
        )

        sys.exit(1)

    window = MainWindow(
        database_path=database_path
    )

    window.showMaximized()

    # Sau khi giao diện chính đã xuất hiện
    # mới bắt đầu preload các thư viện nặng.
    QTimer.singleShot(
        500,
        window.start_chart_preload,
    )

    QTimer.singleShot(
        500,
        window.start_mail_preload,
    )

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()