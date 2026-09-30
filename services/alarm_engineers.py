"""Engineer options in UTF-8 config next to the shared database."""
import json
from pathlib import Path


def load_engineers(database_path):
    path = Path(database_path).parent / "engineers.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        names = data["engineers"]
        if not isinstance(names, list) or any(
            not isinstance(name, str) or not name.strip() for name in names
        ):
            raise ValueError("engineers phải là danh sách tên không rỗng")
        return list(dict.fromkeys(name.strip() for name in names))
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError(f"Không đọc được {path}: {error}") from error
