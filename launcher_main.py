from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import traceback

from ctypes import wintypes
from datetime import datetime
from pathlib import Path


APP_NAME = "Aging Yield"
LOCAL_FOLDER_NAME = "Aging_Yield"
CORE_EXE_NAME = "Aging_Yield.exe"

MUTEX_NAME = (
    "Local\\AgingYieldLauncher"
)


def show_error(
    message: str,
) -> None:
    """Hiển thị lỗi khi Launcher không có console."""

    ctypes.windll.user32.MessageBoxW(
        None,
        message,
        f"{APP_NAME} Launcher",
        0x10,
    )


def show_information(
    message: str,
) -> None:
    """Hiển thị thông báo cho người dùng."""

    ctypes.windll.user32.MessageBoxW(
        None,
        message,
        f"{APP_NAME} Launcher",
        0x40,
    )


def acquire_single_instance():
    """
    Không cho hai Launcher cập nhật
    đồng thời trên cùng một máy.
    """

    kernel32 = ctypes.WinDLL(
        "kernel32",
        use_last_error=True,
    )

    kernel32.CreateMutexW.argtypes = [
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    ]

    kernel32.CreateMutexW.restype = (
        wintypes.HANDLE
    )

    kernel32.CloseHandle.argtypes = [
        wintypes.HANDLE,
    ]

    kernel32.CloseHandle.restype = (
        wintypes.BOOL
    )

    mutex_handle = (
        kernel32.CreateMutexW(
            None,
            False,
            MUTEX_NAME,
        )
    )

    if not mutex_handle:
        raise ctypes.WinError(
            ctypes.get_last_error()
        )

    # ERROR_ALREADY_EXISTS
    if ctypes.get_last_error() == 183:
        kernel32.CloseHandle(
            mutex_handle
        )

        return None

    return (
        kernel32,
        mutex_handle,
    )


class UpdateService:
    """
    Kiểm tra phiên bản, copy package
    và mở Aging Yield.
    """

    def __init__(self) -> None:
        self.server_root = (
            self.get_server_root()
        )

        self.server_package = (
            self.server_root
            / "package"
        )

        self.server_version = (
            self.server_package
            / "version.txt"
        )

        self.server_exe = (
            self.server_package
            / CORE_EXE_NAME
        )

        self.server_internal = (
            self.server_package
            / "_internal"
        )

        self.server_db = (
            self.server_root
            / "database"
            / "aging_monitoring.db"
        )
        self.database_folder = (
                self.server_root
                / "database"
        )

        self.database_create_flag = (
                self.database_folder
                / "allow_create_database.flag"
        )

        self.database_initializing_flag = (
                self.database_folder
                / "database_initializing.flag"
        )

        self.local_root = (
            Path(
                os.environ["LOCALAPPDATA"]
            )
            / LOCAL_FOLDER_NAME
        )

        self.local_app_root = (
            self.local_root
            / "App"
        )

        # Folder copy tạm.
        self.local_staging = (
            self.local_root
            / "App.new"
        )

        # Folder backup tạm.
        self.local_backup = (
            self.local_root
            / "App.backup"
        )

        self.local_version = (
            self.local_app_root
            / "version.txt"
        )

        self.local_exe = (
            self.local_app_root
            / CORE_EXE_NAME
        )

        self.local_internal = (
            self.local_app_root
            / "_internal"
        )

        self.log_file = (
            self.local_root
            / "logs"
            / "launcher.log"
        )

    @staticmethod
    def get_server_root() -> Path:
        """
        Khi build, server root là folder
        chứa Aging_Yield_Launcher.exe.
        """

        if getattr(
            sys,
            "frozen",
            False,
        ):
            return (
                Path(sys.executable)
                .resolve()
                .parent
            )

        return (
            Path(__file__)
            .resolve()
            .parent
        )

    def write_log(
        self,
        message: str,
    ) -> None:
        """Ghi log riêng trên máy người dùng."""

        try:
            self.log_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            timestamp = (
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )

            with self.log_file.open(
                "a",
                encoding="utf-8",
            ) as log_file:
                log_file.write(
                    f"[{timestamp}] "
                    f"{message}\n"
                )

        except Exception:
            pass

    @staticmethod
    def read_optional_text(
        path: Path,
    ) -> str:
        """
        Đọc version local.

        Trả về rỗng nếu máy chưa có app.
        """

        try:
            if path.is_file():
                return path.read_text(
                    encoding="utf-8"
                ).strip()

        except OSError:
            return ""

        return ""

    @staticmethod
    def read_required_text(
        path: Path,
    ) -> str:
        """
        Đọc file bắt buộc.

        Không che giấu lỗi đọc server.
        """

        value = path.read_text(
            encoding="utf-8"
        ).strip()

        if not value:
            raise ValueError(
                "File phiên bản đang rỗng:\n"
                f"{path}"
            )

        return value

    def validate_server(self) -> None:
        """
        Kiểm tra package và trạng thái database.

        Chỉ cho phép tạo database nếu có
        file allow_create_database.flag.
        """

        if not self.server_package.is_dir():
            raise FileNotFoundError(
                "Không tìm thấy package:\n"
                f"{self.server_package}"
            )

        if not self.server_version.is_file():
            raise FileNotFoundError(
                "Không tìm thấy version.txt:\n"
                f"{self.server_version}"
            )

        if not self.server_exe.is_file():
            raise FileNotFoundError(
                "Không tìm thấy Aging_Yield.exe:\n"
                f"{self.server_exe}"
            )

        if not self.server_internal.is_dir():
            raise FileNotFoundError(
                "Không tìm thấy folder _internal:\n"
                f"{self.server_internal}"
            )

        self.read_required_text(
            self.server_version
        )

        # Một máy khác đang khởi tạo DB.
        if (
                self.database_initializing_flag
                        .is_file()
        ):
            raise RuntimeError(
                "Database đang được khởi tạo "
                "bởi một máy khác.\n\n"
                "Vui lòng đợi quá trình hoàn tất "
                "rồi mở lại Aging Yield."
            )

        # Database đã tồn tại, tiếp tục bình thường.
        if self.server_db.is_file():
            return

        # Chưa có DB và cũng không có quyền khởi tạo.
        if not self.database_create_flag.is_file():
            raise FileNotFoundError(
                "Không tìm thấy database dùng chung:\n"
                f"{self.server_db}\n\n"
                "Launcher không tự tạo database vì "
                "đây có thể là trường hợp database "
                "bị đổi tên, bị xóa hoặc mất kết nối mạng.\n\n"
                "Nếu đây là lần triển khai đầu tiên, "
                "hãy tạo file:\n"
                f"{self.database_create_flag}"
            )

    def get_versions(
        self,
    ) -> tuple[str, str]:
        """Lấy version server và local."""

        server_version = (
            self.read_required_text(
                self.server_version
            )
        )

        local_version = (
            self.read_optional_text(
                self.local_version
            )
        )

        return (
            server_version,
            local_version,
        )

    def need_update(self) -> bool:
        """Kiểm tra có cần copy package không."""

        (
            server_version,
            local_version,
        ) = self.get_versions()

        return any((
            server_version
            != local_version,

            not self.local_exe.is_file(),

            not self.local_internal.is_dir(),
        ))

    @staticmethod
    def is_core_running() -> bool:
        """Kiểm tra Aging Yield đang mở."""

        result = subprocess.run(
            [
                "tasklist",
                "/FI",
                (
                    "IMAGENAME eq "
                    f"{CORE_EXE_NAME}"
                ),
            ],
            capture_output=True,
            text=True,
            shell=False,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
            ),
            check=False,
        )

        return (
            CORE_EXE_NAME.lower()
            in result.stdout.lower()
        )

    @staticmethod
    def remove_folder(
        path: Path,
    ) -> None:
        """Xóa folder tạm nếu tồn tại."""

        if path.is_dir():
            shutil.rmtree(path)

    def copy_to_staging(self) -> None:
        """
        Copy package server vào App.new.

        Chưa đụng tới bản App hiện tại.
        """

        self.local_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.remove_folder(
            self.local_staging
        )

        command = [
            "robocopy",
            str(self.server_package),
            str(self.local_staging),
            "/MIR",
            "/R:2",
            "/W:1",
            "/NFL",
            "/NDL",
            "/NJH",
            "/NJS",
            "/NP",
        ]

        self.write_log(
            "Run robocopy: "
            + subprocess.list2cmdline(
                command
            )
        )

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=False,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
            ),
            check=False,
        )

        self.write_log(
            "Robocopy return code: "
            f"{result.returncode}"
        )

        if result.stdout:
            self.write_log(
                result.stdout
            )

        if result.stderr:
            self.write_log(
                result.stderr
            )

        # Robocopy code 0–7 là thành công.
        if result.returncode >= 8:
            raise RuntimeError(
                "Copy chương trình thất bại.\n"
                "Robocopy code: "
                f"{result.returncode}"
            )

    def validate_staging(
        self,
        expected_version: str,
    ) -> None:
        """
        Kiểm tra App.new đầy đủ trước
        khi thay bản local hiện tại.
        """

        staging_exe = (
            self.local_staging
            / CORE_EXE_NAME
        )

        staging_internal = (
            self.local_staging
            / "_internal"
        )

        staging_version_path = (
            self.local_staging
            / "version.txt"
        )

        if not staging_exe.is_file():
            raise FileNotFoundError(
                "Package copy về thiếu "
                "Aging_Yield.exe."
            )

        if not staging_internal.is_dir():
            raise FileNotFoundError(
                "Package copy về thiếu "
                "folder _internal."
            )

        copied_version = (
            self.read_required_text(
                staging_version_path
            )
        )

        if copied_version != expected_version:
            raise RuntimeError(
                "Version package copy về "
                "không khớp version trên server."
            )

    def activate_staging(self) -> None:
        """
        Đưa App.new thành App sau khi
        package được kiểm tra thành công.
        """

        self.remove_folder(
            self.local_backup
        )

        old_app_moved = False

        try:
            if self.local_app_root.is_dir():
                self.local_app_root.rename(
                    self.local_backup
                )

                old_app_moved = True

            self.local_staging.rename(
                self.local_app_root
            )

        except Exception:
            # Khôi phục bản cũ nếu đổi
            # package mới thất bại.
            if (
                old_app_moved
                and not self.local_app_root.exists()
                and self.local_backup.is_dir()
            ):
                self.local_backup.rename(
                    self.local_app_root
                )

            raise

        try:
            self.remove_folder(
                self.local_backup
            )

        except Exception as error:
            self.write_log(
                "Không thể xóa App.backup: "
                f"{error}"
            )

    def copy_package(self) -> None:
        """
        Copy và kích hoạt phiên bản mới
        theo cơ chế an toàn.
        """

        if self.is_core_running():
            raise RuntimeError(
                "Aging Yield đang mở.\n\n"
                "Vui lòng đóng chương trình "
                "rồi mở lại để cập nhật."
            )

        expected_version = (
            self.read_required_text(
                self.server_version
            )
        )

        self.copy_to_staging()

        self.validate_staging(
            expected_version
        )

        self.activate_staging()

        self.write_log(
            "Cập nhật thành công lên "
            f"version {expected_version}."
        )

    def prepare_database(
            self,
    ) -> bool:
        """
        Chuẩn bị database trước khi mở app.

        Trả về True nếu đây là lần đầu
        cần tạo database.
        """

        if self.server_db.is_file():
            return False

        if (
                self.database_initializing_flag
                        .is_file()
        ):
            raise RuntimeError(
                "Database đang được khởi tạo "
                "bởi một máy khác."
            )

        if not self.database_create_flag.is_file():
            raise FileNotFoundError(
                "Không tìm thấy database và "
                "không được phép tạo database mới."
            )

        try:
            # Rename trên cùng ổ mạng dùng để
            # giành quyền khởi tạo database.
            self.database_create_flag.replace(
                self.database_initializing_flag
            )

        except FileNotFoundError as error:
            raise RuntimeError(
                "Một máy khác vừa bắt đầu "
                "khởi tạo database.\n\n"
                "Vui lòng đợi rồi mở lại."
            ) from error

        self.write_log(
            "Đã nhận quyền khởi tạo "
            "database lần đầu."
        )

        return True
    def start_core_app(self) -> None:
        """
        Chuẩn bị database, truyền đường dẫn
        và mở Aging Yield trên máy local.
        """

        if not self.local_exe.is_file():
            raise FileNotFoundError(
                "Không tìm thấy chương trình local:\n"
                f"{self.local_exe}"
            )

        allow_database_creation = (
            self.prepare_database()
        )

        environment = os.environ.copy()

        environment["AGING_DB_PATH"] = str(
            self.server_db
        )

        environment[
            "AGING_SERVER_ROOT"
        ] = str(
            self.server_root
        )

        environment[
            "AGING_ALLOW_DB_CREATE"
        ] = (
            "1"
            if allow_database_creation
            else "0"
        )

        try:
            subprocess.Popen(
                [str(self.local_exe)],
                env=environment,
                cwd=str(
                    self.local_app_root
                ),
            )

        except Exception:
            # Aging Yield chưa mở được nên trả lại
            # quyền khởi tạo cho lần thử tiếp theo.
            if (
                    allow_database_creation
                    and self.database_initializing_flag
                    .is_file()
                    and not self.server_db.is_file()
            ):
                self.database_initializing_flag.replace(
                    self.database_create_flag
                )

            raise

    def run(self) -> None:
        """Thực hiện toàn bộ luồng Launcher."""

        self.validate_server()

        (
            server_version,
            local_version,
        ) = self.get_versions()

        self.write_log(
            "Launcher start | "
            f"Server: {server_version} | "
            f"Local: {local_version or 'NONE'}"
        )

        if self.need_update():
            self.copy_package()

        elif self.is_core_running():
            show_information(
                "Aging Yield đang được mở."
            )

            return

        self.start_core_app()

        self.write_log(
            "Đã mở Aging Yield."
        )

    def log_exception(self) -> None:
        """Ghi chi tiết lỗi Launcher."""

        self.write_log(
            traceback.format_exc().rstrip()
        )


def main() -> int:
    """Entry point Aging Yield Launcher."""

    if os.name != "nt":
        return 1

    mutex = acquire_single_instance()

    if mutex is None:
        return 0

    (
        kernel32,
        mutex_handle,
    ) = mutex

    service = UpdateService()

    try:
        service.run()

        return 0

    except Exception as error:
        service.log_exception()

        error_message = str(
            error
        ).strip()

        show_error(
            error_message
            or "Launcher gặp lỗi không xác định."
        )

        return 1

    finally:
        kernel32.CloseHandle(
            mutex_handle
        )


if __name__ == "__main__":
    sys.exit(
        main()
    )