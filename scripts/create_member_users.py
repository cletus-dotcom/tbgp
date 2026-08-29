"""Create Member-role users for members from ID 1001 onward.

Username and password default to the member ID (e.g. 1001 / 1001).
Skips members that already have a linked user or whose username is taken.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["TBGP_SKIP_DATA_SEED"] = "1"

from app import create_app, db
from app.config import USER_ROLE_MEMBER
from app.models import Member, User

START_MEMBER_ID = 1001


def main():
    app = create_app()
    with app.app_context():
        db.session.rollback()
        members = (
            Member.query
            .filter(Member.member_id >= START_MEMBER_ID)
            .order_by(Member.member_id.asc())
            .all()
        )
        if not members:
            raise SystemExit(f"No members found with member_id >= {START_MEMBER_ID}")

        created = 0
        skipped_linked = 0
        skipped_username = 0

        for member in members:
            username = str(member.member_id)
            password = username
            full_name = member.full_name or username

            if User.query.filter_by(member_id=member.member_id).first():
                skipped_linked += 1
                continue

            if User.query.filter_by(username=username).first():
                skipped_username += 1
                continue

            user = User(
                username=username,
                full_name=full_name,
                role=USER_ROLE_MEMBER,
                status="Active",
                member_id=member.member_id,
            )
            user.set_password(password)
            db.session.add(user)
            created += 1

        db.session.commit()
        print({
            "members_scanned": len(members),
            "created": created,
            "skipped_already_linked": skipped_linked,
            "skipped_username_taken": skipped_username,
            "first_id": members[0].member_id,
            "last_id": members[-1].member_id,
            "total_member_users": User.query.filter_by(role=USER_ROLE_MEMBER).count(),
        })


if __name__ == "__main__":
    main()
