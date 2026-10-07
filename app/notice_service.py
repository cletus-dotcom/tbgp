"""Policies, memos, and announcements for role dashboards."""

from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.config import (
    NOTICE_TYPE_LABELS,
    NOTICE_TYPES,
    USER_ROLES,
    can_manage_notices,
    normalize_role,
)
from app.models import PortalNotice, PortalNoticeRead
from app.timeutil import manila_now


_UNSET = object()


def notice_type_label(notice_type):
    return NOTICE_TYPE_LABELS.get(notice_type, (notice_type or "").title())


def _parse_optional_date(raw, label):
    if isinstance(raw, date):
        return raw
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Invalid {label}. Use YYYY-MM-DD.") from exc


def _clean_optional_text(raw, label, max_length):
    text = (raw or "").strip()
    if len(text) > max_length:
        raise ValueError(f"{label} must be {max_length} characters or fewer.")
    return text or None


def _check_reference_number(notice_type, reference_number, exclude_id=None):
    """Reference numbers must be unique within a notice type (case-insensitive)."""
    if not reference_number:
        return
    query = PortalNotice.query.filter(
        PortalNotice.notice_type == notice_type,
        func.lower(PortalNotice.reference_number) == reference_number.lower(),
    )
    if exclude_id is not None:
        query = query.filter(PortalNotice.notice_id != exclude_id)
    if query.first():
        raise ValueError(
            f"{notice_type_label(notice_type)} No. {reference_number} is already in use."
        )


def _normalize_audience(roles):
    if not roles:
        return []
    cleaned = []
    seen = set()
    for role in roles:
        normalized = normalize_role(role)
        if normalized in USER_ROLES and normalized not in seen:
            cleaned.append(normalized)
            seen.add(normalized)
    return cleaned


def _audience_includes(notice, role):
    audience = notice.audience_roles or []
    if not audience:
        return True
    return normalize_role(role) in audience


def notices_for_role(role, *, published_only=True, include_unpublished_for_managers=False):
    query = PortalNotice.query.options(joinedload(PortalNotice.created_by))
    if published_only and not (
        include_unpublished_for_managers and can_manage_notices(role)
    ):
        query = query.filter_by(is_published=True)
    notices = query.order_by(PortalNotice.created_at.desc()).all()
    return [n for n in notices if _audience_includes(n, role)]


def unread_notice_ids(user_id, role):
    if not user_id:
        return set()
    visible = notices_for_role(role, published_only=True)
    if not visible:
        return set()
    visible_ids = [n.notice_id for n in visible]
    read_ids = {
        row.notice_id
        for row in PortalNoticeRead.query.filter(
            PortalNoticeRead.user_id == user_id,
            PortalNoticeRead.notice_id.in_(visible_ids),
        ).all()
    }
    return set(visible_ids) - read_ids


def unread_notice_count(user_id, role):
    return len(unread_notice_ids(user_id, role))


def notice_to_dict(notice, *, user_id=None, unread_ids=None):
    audience = notice.audience_roles or []
    is_unread = False
    if unread_ids is not None:
        is_unread = notice.notice_id in unread_ids
    elif user_id:
        is_unread = (
            PortalNoticeRead.query.filter_by(
                notice_id=notice.notice_id, user_id=user_id
            ).first()
            is None
        )
    return {
        "notice_id": notice.notice_id,
        "notice_type": notice.notice_type,
        "notice_type_label": notice_type_label(notice.notice_type),
        "title": notice.title,
        "body": notice.body,
        "reference_number": notice.reference_number or "",
        "effective_date": notice.effective_date,
        "issued_by": notice.issued_by or "",
        "issued_date": notice.issued_date,
        "audience_roles": audience,
        "audience_label": "All roles" if not audience else ", ".join(audience),
        "is_published": bool(notice.is_published),
        "created_by_user_id": notice.created_by_user_id,
        "created_by_name": (
            notice.created_by.full_name
            if notice.created_by and notice.created_by.full_name
            else (notice.created_by.username if notice.created_by else "—")
        ),
        "created_at": notice.created_at,
        "updated_at": notice.updated_at,
        "is_unread": is_unread,
    }


def dashboard_notices(user_id, role, limit=5):
    unread = unread_notice_ids(user_id, role)
    notices = notices_for_role(role, published_only=True)
    rows = [notice_to_dict(n, unread_ids=unread) for n in notices[:limit]]
    return {
        "items": rows,
        "unread_count": len(unread),
        "total_count": len(notices),
    }


def get_notice(notice_id):
    return db.session.get(PortalNotice, notice_id)


def get_visible_notice(notice_id, role):
    notice = get_notice(notice_id)
    if not notice:
        return None
    if not notice.is_published and not can_manage_notices(role):
        return None
    if not _audience_includes(notice, role):
        return None
    return notice


def mark_notice_read(notice_id, user_id):
    if not notice_id or not user_id:
        return
    existing = PortalNoticeRead.query.filter_by(
        notice_id=notice_id, user_id=user_id
    ).first()
    if existing:
        return
    db.session.add(
        PortalNoticeRead(
            notice_id=notice_id,
            user_id=user_id,
            read_at=manila_now(),
        )
    )
    db.session.commit()


def create_notice(
    *,
    notice_type,
    title,
    body,
    reference_number=None,
    effective_date=None,
    issued_by=None,
    issued_date=None,
    audience_roles=None,
    is_published=True,
    created_by_user_id=None,
):
    notice_type = (notice_type or "").strip().lower()
    if notice_type not in NOTICE_TYPES:
        raise ValueError("Invalid notice type.")
    title = (title or "").strip()
    body = (body or "").strip()
    if not title:
        raise ValueError("Title is required.")
    if not body:
        raise ValueError("Body is required.")
    reference_number = _clean_optional_text(reference_number, "Policy/Memo No.", 60)
    _check_reference_number(notice_type, reference_number)

    now = manila_now()
    notice = PortalNotice(
        notice_type=notice_type,
        title=title,
        body=body,
        reference_number=reference_number,
        effective_date=_parse_optional_date(effective_date, "effectivity date"),
        issued_by=_clean_optional_text(issued_by, "Issued by", 160),
        issued_date=_parse_optional_date(issued_date, "date issued"),
        audience_roles=_normalize_audience(audience_roles),
        is_published=bool(is_published),
        created_by_user_id=created_by_user_id,
        created_at=now,
        updated_at=now,
    )
    db.session.add(notice)
    db.session.commit()
    return notice


def update_notice(
    notice,
    *,
    notice_type=None,
    title=None,
    body=None,
    reference_number=_UNSET,
    effective_date=_UNSET,
    issued_by=_UNSET,
    issued_date=_UNSET,
    audience_roles=None,
    is_published=None,
):
    if notice_type is not None:
        notice_type = notice_type.strip().lower()
        if notice_type not in NOTICE_TYPES:
            raise ValueError("Invalid notice type.")
        notice.notice_type = notice_type
    if reference_number is not _UNSET:
        notice.reference_number = _clean_optional_text(reference_number, "Policy/Memo No.", 60)
    if reference_number is not _UNSET or notice_type is not None:
        _check_reference_number(notice.notice_type, notice.reference_number, exclude_id=notice.notice_id)
    if effective_date is not _UNSET:
        notice.effective_date = _parse_optional_date(effective_date, "effectivity date")
    if issued_by is not _UNSET:
        notice.issued_by = _clean_optional_text(issued_by, "Issued by", 160)
    if issued_date is not _UNSET:
        notice.issued_date = _parse_optional_date(issued_date, "date issued")
    if title is not None:
        title = title.strip()
        if not title:
            raise ValueError("Title is required.")
        notice.title = title
    if body is not None:
        body = body.strip()
        if not body:
            raise ValueError("Body is required.")
        notice.body = body
    if audience_roles is not None:
        notice.audience_roles = _normalize_audience(audience_roles)
    if is_published is not None:
        notice.is_published = bool(is_published)
    notice.updated_at = manila_now()
    db.session.commit()
    return notice


def delete_notice(notice):
    db.session.delete(notice)
    db.session.commit()


def list_manageable_notices():
    return (
        PortalNotice.query.options(joinedload(PortalNotice.created_by))
        .order_by(PortalNotice.created_at.desc())
        .all()
    )
