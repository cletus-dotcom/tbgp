"""Portal positions per department and member position assignments."""

from datetime import datetime

from sqlalchemy import func

from app import db
from app.config import DEPARTMENTS, normalize_department
from app.models import MemberPosition, PortalPosition
from app.timeutil import manila_now


def positions_by_department():
    """Return {department: [PortalPosition, ...]} for every department, in display order."""
    grouped = {department: [] for department in DEPARTMENTS}
    rows = PortalPosition.query.order_by(
        PortalPosition.sort_order.asc(), PortalPosition.title.asc()
    ).all()
    for row in rows:
        grouped.setdefault(row.department, []).append(row)
    return grouped


def assignment_counts():
    """Return {position_id: number of members holding it}."""
    rows = (
        db.session.query(MemberPosition.position_id, func.count(MemberPosition.member_position_id))
        .group_by(MemberPosition.position_id)
        .all()
    )
    return {position_id: count for position_id, count in rows}


def _require_department(raw):
    department = normalize_department(raw)
    if not department:
        raise ValueError("Choose a valid department.")
    return department


def _require_title(raw):
    title = (raw or "").strip()
    if not title:
        raise ValueError("Position title is required.")
    if len(title) > 120:
        raise ValueError("Position title must be 120 characters or fewer.")
    return title


def _title_taken(department, title, exclude_id=None):
    query = PortalPosition.query.filter(
        PortalPosition.department == department,
        func.lower(PortalPosition.title) == title.lower(),
    )
    if exclude_id is not None:
        query = query.filter(PortalPosition.position_id != exclude_id)
    return query.first() is not None


def create_position(department, title):
    department = _require_department(department)
    title = _require_title(title)
    if _title_taken(department, title):
        raise ValueError(f"'{title}' already exists in {department}.")
    next_order = (
        db.session.query(func.coalesce(func.max(PortalPosition.sort_order), 0))
        .filter(PortalPosition.department == department)
        .scalar()
        + 1
    )
    position = PortalPosition(
        department=department,
        title=title,
        sort_order=next_order,
        created_at=manila_now(),
    )
    db.session.add(position)
    db.session.commit()
    return position


def rename_position(position_id, title):
    position = db.session.get(PortalPosition, position_id)
    if not position:
        raise ValueError("Position not found.")
    title = _require_title(title)
    if _title_taken(position.department, title, exclude_id=position.position_id):
        raise ValueError(f"'{title}' already exists in {position.department}.")
    position.title = title
    db.session.commit()
    return position


def delete_position(position_id):
    position = db.session.get(PortalPosition, position_id)
    if not position:
        raise ValueError("Position not found.")
    in_use = MemberPosition.query.filter_by(position_id=position.position_id).count()
    if in_use:
        raise ValueError(
            f"'{position.title}' is assigned to {in_use} member(s). "
            "Reassign them before deleting this position."
        )
    db.session.delete(position)
    db.session.commit()


def apply_member_positions(member, data):
    """Set one position per department from form fields named ``position_<Department>``.

    Blank selects clear that department. Does not commit; callers commit with the member.
    """
    current = member.positions_by_department()
    for department in DEPARTMENTS:
        raw = (data.get(f"position_{department}") or "").strip()
        existing = current.get(department)

        if not raw:
            if existing:
                member.positions.remove(existing)
            continue

        if not raw.isdigit():
            raise ValueError(f"Invalid position for {department}.")
        position = db.session.get(PortalPosition, int(raw))
        if not position or position.department != department:
            raise ValueError(f"Selected position does not belong to {department}.")

        if existing:
            if existing.position_id != position.position_id:
                existing.position = position
                existing.assigned_at = manila_now()
        else:
            member.positions.append(
                MemberPosition(
                    department=department,
                    position=position,
                    assigned_at=manila_now(),
                )
            )
