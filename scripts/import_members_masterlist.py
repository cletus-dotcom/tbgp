"""One-off member replace import from the masterlist workbook."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["TBGP_SKIP_DATA_SEED"] = "1"

from app import create_app, db
from app.db_migrate import migrate_members_table
from app.import_service import import_members_from_xlsx

SOURCE = Path(r"c:\Users\jagna\MICT\docs\tbgp\MASTERLIST-members_import_082826.xlsx")
DEST = ROOT / "data" / "members.xlsx"


def main():
    if not SOURCE.exists():
        raise SystemExit(f"Source file not found: {SOURCE}")

    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_bytes(SOURCE.read_bytes())

    app = create_app()
    with app.app_context():
        db.session.rollback()
        migrate_members_table()
        db.session.commit()
        result = import_members_from_xlsx(SOURCE, replace=True, actor_role="Admin")
        print(result)


if __name__ == "__main__":
    main()
