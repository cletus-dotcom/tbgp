"""Run database migrations and seeds once (e.g. before deploy or after schema changes)."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["TBGP_SKIP_STARTUP_TASKS"] = "1"
os.environ.setdefault("TBGP_SKIP_DATA_SEED", "1")

from app import create_app, db
from app.startup import initialize_database


def main():
    app = create_app()
    with app.app_context():
        db.session.rollback()
        initialize_database()
        print("Startup migrations and seeds completed.")


if __name__ == "__main__":
    main()
