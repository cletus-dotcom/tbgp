"""User duties (Project Coordinator, Account Officer, ...) and the assignee lists they drive."""

import re

from sqlalchemy import func, or_

from app import db
from app.config import (
    DUTY_LABELS,
    DUTY_PROJECT_COORDINATOR,
    MEMBER_FIELD_DUTIES,
    PRODUCT_MEMBER_DUTIES,
    TEAM_SLOT_COLUMNS,
    TRANSACTION_TYPE_PROJECTS,
    USER_ROLE_ADMIN,
    USER_ROLE_MEMBER,
    USER_ROLE_PORTAL_ADMIN,
    USER_ROLE_STAFF,
    duties_allowed_for_role,
    is_member_role,
    is_staff_or_admin,
    member_duties_for_type,
    team_slots_for_type,
)
from app.models import MarketplaceLead, User, UserDuty
from app.timeutil import manila_now

STAFF_ROLES = (USER_ROLE_PORTAL_ADMIN, USER_ROLE_ADMIN, USER_ROLE_STAFF)
_PERSON_TITLES = re.compile(
    r"\b(engr|engineer|eng|archt|arch|architect|sir|maam|mr|ms|mrs|atty|foreman)\b\.?", re.I
)


def duty_label(duty):
    return DUTY_LABELS.get(duty, duty or "")


def person_key(name):
    """Lower-case name without titles or punctuation ("Engr.  Junji" -> "junji")."""
    text = _PERSON_TITLES.sub(" ", name or "")
    text = re.sub(r"[^a-z ]", " ", text.lower())
    return " ".join(text.split())


def _active(query):
    return query.filter(or_(User.status.is_(None), User.status == "Active"))


def set_user_duties(user, duty_keys):
    """Replace the user's duties; returns the list of newly granted duties."""
    allowed = duties_allowed_for_role(user.role)
    wanted = {key for key in duty_keys if key}
    invalid = wanted - set(allowed)
    if invalid:
        names = ", ".join(duty_label(key) for key in sorted(invalid))
        raise ValueError(f"{user.role} accounts cannot hold: {names}.")
    current = {row.duty: row for row in user.duty_rows}
    for duty, row in current.items():
        if duty not in wanted:
            user.duty_rows.remove(row)
    added = []
    for duty in sorted(wanted - set(current)):
        user.duty_rows.append(UserDuty(duty=duty, created_at=manila_now()))
        added.append(duty)
    return added


def duty_holders(duty):
    return (
        _active(User.query.join(UserDuty, UserDuty.user_id == User.user_id))
        .filter(UserDuty.duty == duty, User.role.in_((*STAFF_ROLES, USER_ROLE_MEMBER)))
        .order_by(func.coalesce(User.full_name, User.username).asc())
        .all()
    )


def staff_users():
    return (
        _active(User.query.filter(User.role.in_(STAFF_ROLES)))
        .order_by(func.coalesce(User.full_name, User.username).asc())
        .all()
    )


def assignee_choices(duty=None, include_ids=()):
    """Holders of the duty (Staff/Admin fallback when nobody holds it yet) plus current picks.

    Sales agents have no fallback: the slot stays empty until someone holds the duty.
    """
    users = duty_holders(duty) if duty else []
    if not users and duty not in PRODUCT_MEMBER_DUTIES:
        users = staff_users()
    seen = {u.user_id for u in users}
    extra = [uid for uid in include_ids if uid and uid not in seen]
    if extra:
        users = users + User.query.filter(User.user_id.in_(extra)).all()
    return users


def field_agents_for_type(transaction_type):
    """Members holding a field duty for the transaction type (project field agents or sales agents)."""
    duties = member_duties_for_type(transaction_type)
    if not duties:
        return []
    return (
        _active(User.query)
        .filter(
            User.role == USER_ROLE_MEMBER,
            User.duty_rows.any(UserDuty.duty.in_(duties)),
        )
        .order_by(func.coalesce(User.full_name, User.username).asc())
        .all()
    )


def field_agents():
    """Members holding a project field duty (for schedule assignment on projects)."""
    return field_agents_for_type(TRANSACTION_TYPE_PROJECTS)


def can_be_assigned(user, transaction_type=None, duty=None):
    """Staff/Admin can always be assigned; Members only for a field duty of that transaction type they hold."""
    if user is None:
        return False
    if user.status not in (None, "Active"):
        return False
    if is_staff_or_admin(user.role):
        return True
    member_duties = set(member_duties_for_type(transaction_type))
    if is_member_role(user.role) and member_duties:
        held = user.duty_keys & member_duties
        return bool(held) if duty is None else duty in held
    return False


def user_has_field_duty(user_id):
    return db.session.query(
        UserDuty.query.filter(UserDuty.user_id == user_id, UserDuty.duty.in_(MEMBER_FIELD_DUTIES)).exists()
    ).scalar()


def is_field_agent(user):
    return user is not None and is_member_role(user.role) and bool(user.duty_keys & set(MEMBER_FIELD_DUTIES))


def team_filter(user_id):
    """Transactions where the user holds any team slot (project or product team)."""
    return or_(*(getattr(MarketplaceLead, column) == user_id for column in TEAM_SLOT_COLUMNS))


def team_slots_for(lead, user_id):
    return [slot for slot in team_slots_for_type(lead.transaction_type) if getattr(lead, slot) == user_id]


def match_coordinator(name, holders=None):
    """The single coordinator-duty holder whose name matches a sheet name, else None."""
    key = person_key(name)
    if not key:
        return None
    holders = duty_holders(DUTY_PROJECT_COORDINATOR) if holders is None else holders
    full = [u for u in holders if person_key(u.full_name or u.username) == key]
    if len(full) == 1:
        return full[0]
    first = [u for u in holders if (person_key(u.full_name or u.username).split() or [""])[0] == key.split()[0]]
    return first[0] if len(first) == 1 else None


def link_sheet_coordinators(user=None):
    """Assign unassigned projects whose sheet coordinator name matches a coordinator; returns count."""
    holders = duty_holders(DUTY_PROJECT_COORDINATOR)
    if user is not None and user.user_id not in {u.user_id for u in holders}:
        return 0
    leads = MarketplaceLead.query.filter(
        MarketplaceLead.transaction_type == TRANSACTION_TYPE_PROJECTS,
        MarketplaceLead.assigned_user_id.is_(None),
        MarketplaceLead.project_coordinator.isnot(None),
    ).all()
    from app.transaction_service import _append_history

    linked = 0
    for lead in leads:
        match = match_coordinator(lead.project_coordinator, holders)
        if match is None or (user is not None and match.user_id != user.user_id):
            continue
        lead.assigned_user_id = match.user_id
        _append_history(
            lead,
            event_type="update",
            note=f"Project coordinator linked to {match.full_name or match.username} (sheet name '{lead.project_coordinator}')",
            user_id=None,
        )
        linked += 1
    return linked
