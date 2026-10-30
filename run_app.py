"""Start the demo app locally: python run_app.py, then open http://127.0.0.1:5000."""
import tempfile
from pathlib import Path

from app import create_app

if __name__ == "__main__":
    db_path = Path(tempfile.mkdtemp(prefix="taskboard-")) / "taskboard.db"
    create_app(db_path).run(host="127.0.0.1", port=5000)
