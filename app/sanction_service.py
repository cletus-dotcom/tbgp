"""Member suspensions: blocking ad posting and contractor endorsement for a fixed period."""

from datetime import date, datetime, timedelta

from sqlalchemy.orm import joinedload

from app import db
from app.config import SANCTION_DEFAULT_DAYS, SANCTION_MAX_DAYS
from app.models import Member, MemberSanction
from app.timeutil import manila_now, manila_today

SANCTION_KIND_ADS = "ads"
SANCTION_KIND_ENDORSEMENT = "endorsement"

SANCTION_STATUS_LABELS = {
    "active": "Active",
    "scheduled": "Scheduled",
    "served": "Served",
    "lifted": "Lifted early",
}


def format_day(value):
    return value.strftime("%b %d, %Y").replace(" 0", " ") if value else ""


def _as_day(value):
    if isinstance(value, datetime):
        return value.date()
    return value


def _active_query(on=None):
    day = _as_day(on) or manila_today()
    return MemberSanction.query.filter(
        MemberSanction.lifted_at.is_(None),
        MemberSanction.start_date <= day,
        MemberSanction.end_date >= day,
    )


def active_sanction(member_id, kind=None, on=None):
    """The longest-running suspension in force for this member on the given day."""
    if not member_id:
        return None
    query = _active_query(on).filter(MemberSanction.member_id == member_id)
    if kind == SANCTION_KIND_ADS:
        query = query.filter(MemberSanction.blocks_ads.is_(True))
    elif kind == SANCTION_KIND_ENDORSEMENT:
        query = query.filter(MemberSanction.blocks_endorsement.is_(True))
    return query.order_by(MemberSanction.end_date.desc()).first()


def is_ads_suspended(member_id, on=None):
    return active_sanction(member_id, SANCTION_KIND_ADS, on) is not None


def is_endorsement_suspended(member_id, on=None):
    return active_sanction(member_id, SANCTION_KIND_ENDORSEMENT, on) is not None


def _member_label(member_id):
    member = db.session.get(Member, member_id)
    return member.full_name if member else f"Member #{member_id}"


def _memo_suffix(sanction):
    return f" (Memorandum {sanction.memo_number})" if sanction.memo_number else ""


def ensure_can_endorse(member_id, on=None):
    sanction = active_sanction(member_id, SANCTION_KIND_ENDORSEMENT, on)
    if sanction is not None:
        raise ValueError(
            f"{_member_label(member_id)} is suspended from endorsing contractors until "
            f"{format_day(sanction.end_date)}{_memo_suffix(sanction)}. Choose another member referrer."
        )


def endorsement_credit_member_id(member_id, on=None):
    """Who is credited as contractor referrer on a commission record created on the given day.

    A suspended endorser's credit goes to the admin member, the same account that receives
    credit for direct inquiries without a ProF.
    """
    sanction = active_sanction(member_id, SANCTION_KIND_ENDORSEMENT, on)
    if sanction is None:
        return member_id
    from app.prof_sharing_service import get_admin_member

    admin_member = get_admin_member()
    if admin_member is None:
        raise ValueError(
            f"{_member_label(member_id)} is suspended from endorsing contractors until "
            f"{format_day(sanction.end_date)} and no admin member is configured to receive the credit."
        )
    return admin_member.member_id


def _parse_day(raw, label):
    if isinstance(raw, date):
        return raw
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid date.") from exc


def issue_sanction(member_id, reason, user, memo_number=None, start_date=None, days=None,
                   blocks_ads=True, blocks_endorsement=True):
    member = db.session.get(Member, member_id) if member_id else None
    if member is None:
        raise ValueError("Select the member to suspend.")
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Write the reason for the suspension.")
    if not (blocks_ads or blocks_endorsement):
        raise ValueError("Choose at least one privilege to suspend.")
    start = _parse_day(start_date, "Start date") or manila_today()
    try:
        total_days = int(days) if str(days or "").strip() else SANCTION_DEFAULT_DAYS
    except (TypeError, ValueError) as exc:
        raise ValueError("Number of days must be a whole number.") from exc
    if not 1 <= total_days <= SANCTION_MAX_DAYS:
        raise ValueError(f"Number of days must be between 1 and {SANCTION_MAX_DAYS}.")

    sanction = MemberSanction(
        member_id=member.member_id,
        memo_number=(memo_number or "").strip()[:80] or None,
        reason=reason,
        start_date=start,
        end_date=start + timedelta(days=total_days - 1),
        blocks_ads=bool(blocks_ads),
        blocks_endorsement=bool(blocks_endorsement),
        created_by_user_id=user.user_id if user else None,
    )
    db.session.add(sanction)
    db.session.commit()
    return sanction


def lift_sanction(sanction, reason, user):
    if sanction.lifted_at is not None:
        raise ValueError("This suspension was already lifted.")
    if sanction.status_on() == "served":
        raise ValueError("This suspension has already been served.")
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Write why the suspension is being lifted early.")
    sanction.lifted_at = manila_now()
    sanction.lifted_by_user_id = user.user_id if user else None
    sanction.lift_reason = reason[:255]
    db.session.commit()
    return sanction


def get_sanction(sanction_id):
    return db.session.get(MemberSanction, sanction_id)


def list_sanctions(member_id=None):
    query = MemberSanction.query.options(
        joinedload(MemberSanction.member),
        joinedload(MemberSanction.created_by),
        joinedload(MemberSanction.lifted_by),
    )
    if member_id:
        query = query.filter(MemberSanction.member_id == member_id)
    return query.order_by(MemberSanction.start_date.desc(), MemberSanction.sanction_id.desc()).all()


def active_sanction_count():
    return _active_query().count()


def member_violation_count(member_id):
    return MemberSanction.query.filter(MemberSanction.member_id == member_id).count()
