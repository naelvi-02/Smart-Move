from pathlib import Path
import os
import sys

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from runtime_config import get_backend_port, get_data_dir


def main() -> None:
    data_dir = get_data_dir()
    os.environ.setdefault("SMART_MOVE_DATA_DIR", str(data_dir))
    os.environ.setdefault("SMART_MOVE_ENV_PATH", str(data_dir / ".env"))

    import uvicorn
    from main import app

    uvicorn.run(app, host="127.0.0.1", port=get_backend_port(), reload=False)


if __name__ == "__main__":
    main()
