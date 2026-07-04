from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from app import db
from app.config import (
    LEDGER_TRANSACTION_CREDIT,
    LEDGER_TRANSACTION_DEBIT,
    OMPD_FUND_LABEL,
    PAYOUT_OMPD_PERCENT,
    PAYOUT_RELEASE_METHOD_BANK_DEPOSIT,
    PAYOUT_RELEASE_METHOD_OTHER,
    PAYOUT_RELEASE_METHODS,
    PAYOUT_STATUS_APPROVED,
    PAYOUT_STATUS_PENDING,
    PAYOUT_STATUS_REJECTED,
    PAYOUT_STATUS_RELEASED,
    PAYOUT_STATUS_RELEASE_SUBMITTED,
    is_admin_role,
    payout_ompd_split,
    payout_scheme_summary,
)
from app.models import Member, MemberLedger, OmpdFundEntry, PayoutNotification, PayoutRequest, User


RESERVED_STATUSES = (
    PAYOUT_STATUS_PENDING,
    PAYOUT_STATUS_APPROVED,
    PAYOUT_STATUS_RELEASE_SUBMITTED,
)


def _money(value):
    return round(float(value or 0), 2)


def _now():
    return datetime.utcnow()


def _member_name(member):
    return member.full_name if member else "Member"


def _notify_roles(payout, roles, title, message, user_id=None):
    for role in roles:
        db.session.add(PayoutNotification(
            payout_id=payout.payout_id,
            audience_role=role,
            user_id=user_id,
            title=title,
            message=message,
            is_read=False,
            created_at=_now(),
        ))


def _notify_member(payout, member_user_id, title, message):
    if not member_user_id:
        return
    db.session.add(PayoutNotification(
        payout_id=payout.payout_id,
        audience_role="Member",
        user_id=member_user_id,
        title=title,
        message=message,
        is_read=False,
        created_at=_now(),
    ))


def _member_user_id(member_id):
    user = User.query.filter_by(member_id=member_id, status="Active").first()
    return user.user_id if user else None


def member_credit_total(member_id):
    total = (
        db.session.query(func.coalesce(func.sum(MemberLedger.share_amount), 0))
        .filter(
            MemberLedger.member_id == member_id,
            MemberLedger.transaction_type == LEDGER_TRANSACTION_CREDIT,
        )
        .scalar()
    )
    return _money(total)


def member_debit_total(member_id):
    total = (
        db.session.query(func.coalesce(func.sum(MemberLedger.share_amount), 0))
        .filter(
            MemberLedger.member_id == member_id,
            MemberLedger.transaction_type == LEDGER_TRANSACTION_DEBIT,
        )
        .scalar()
    )
    return _money(total)


def member_reserved_payout_total(member_id):
    total = (
        db.session.query(func.coalesce(func.sum(PayoutRequest.requested_amount), 0))
        .filter(
            PayoutRequest.member_id == member_id,
            PayoutRequest.status.in_(RESERVED_STATUSES),
        )
        .scalar()
    )
    return _money(total)


def member_available_balance(member_id):
    credits = Decimal(str(member_credit_total(member_id)))
    debits = Decimal(str(member_debit_total(member_id)))
    reserved = Decimal(str(member_reserved_payout_total(member_id)))
    return _money(credits - debits - reserved)


def payout_request_query(status=None, member_id=None):
    query = (
        PayoutRequest.query
        .options(
            joinedload(PayoutRequest.member),
            joinedload(PayoutRequest.requested_by),
            joinedload(PayoutRequest.request_reviewed_by),
            joinedload(PayoutRequest.release_submitted_by),
            joinedload(PayoutRequest.release_approved_by),
            joinedload(PayoutRequest.rejected_by),
            joinedload(PayoutRequest.ledger_entry),
        )
        .order_by(PayoutRequest.requested_at.desc(), PayoutRequest.payout_id.desc())
    )
    if status:
        if isinstance(status, (list, tuple, set)):
            query = query.filter(PayoutRequest.status.in_(status))
        else:
            query = query.filter(PayoutRequest.status == status)
    if member_id:
        query = query.filter(PayoutRequest.member_id == member_id)
    return query


def _payout_amounts(payout):
    gross = Decimal(str(payout.requested_amount or 0))
    if payout.ompd_deduction is not None and payout.net_release_amount is not None:
        ompd = Decimal(str(payout.ompd_deduction))
        net = Decimal(str(payout.net_release_amount))
    else:
        ompd, net = payout_ompd_split(gross)
    return gross, ompd, net


def payout_to_dict(payout):
    member = payout.member
    gross, ompd, net = _payout_amounts(payout)
    return {
        "payout_id": payout.payout_id,
        "member_id": payout.member_id,
        "member_name": _member_name(member),
        "requested_amount": _money(gross),
        "ompd_deduction": _money(ompd),
        "net_release_amount": _money(net),
        "ompd_percent": PAYOUT_OMPD_PERCENT,
        "status": payout.status,
        "member_note": payout.member_note or "",
        "requested_at": payout.requested_at.isoformat() if payout.requested_at else None,
        "requested_by": payout.requested_by.full_name if payout.requested_by else None,
        "request_reviewed_at": payout.request_reviewed_at.isoformat() if payout.request_reviewed_at else None,
        "request_reviewed_by": payout.request_reviewed_by.full_name if payout.request_reviewed_by else None,
        "request_review_note": payout.request_review_note or "",
        "release_method": payout.release_method or "",
        "release_reference": payout.release_reference or "",
        "release_account_info": payout.release_account_info or "",
        "release_notes": payout.release_notes or "",
        "release_submitted_at": payout.release_submitted_at.isoformat() if payout.release_submitted_at else None,
        "release_submitted_by": payout.release_submitted_by.full_name if payout.release_submitted_by else None,
        "release_approved_at": payout.release_approved_at.isoformat() if payout.release_approved_at else None,
        "release_approved_by": payout.release_approved_by.full_name if payout.release_approved_by else None,
        "released_at": payout.released_at.isoformat() if payout.released_at else None,
        "rejected_at": payout.rejected_at.isoformat() if payout.rejected_at else None,
        "rejected_by": payout.rejected_by.full_name if payout.rejected_by else None,
        "rejection_reason": payout.rejection_reason or "",
        "ledger_id": payout.ledger_entry.ledger_id if payout.ledger_entry else None,
    }


def create_payout_request(member_id, amount, user_id, member_note=None):
    member = db.session.get(Member, member_id)
    if not member:
        raise ValueError("Member not found.")

    amount_dec = Decimal(str(amount)).quantize(Decimal("0.01"))
    if amount_dec <= 0:
        raise ValueError("Payout amount must be greater than zero.")

    ompd_deduction, net_release = payout_ompd_split(amount_dec)
    if net_release <= 0:
        raise ValueError("Payout amount is too small after OMPD deduction.")

    available = Decimal(str(member_available_balance(member_id)))
    if amount_dec > available:
        raise ValueError(
            f"Requested amount exceeds available balance ({_money(available):,.2f})."
        )

    pending_exists = (
        PayoutRequest.query
        .filter(
            PayoutRequest.member_id == member_id,
            PayoutRequest.status.in_(RESERVED_STATUSES),
        )
        .first()
    )
    if pending_exists:
        raise ValueError("You already have an active payout request in progress.")

    payout = PayoutRequest(
        member_id=member_id,
        requested_amount=amount_dec,
        ompd_deduction=ompd_deduction,
        net_release_amount=net_release,
        status=PAYOUT_STATUS_PENDING,
        member_note=(member_note or "").strip() or None,
        requested_at=_now(),
        requested_by_user_id=user_id,
    )
    db.session.add(payout)
    db.session.flush()

    title = "New payout request"
    message = (
        f"Member #{member_id} {_member_name(member)} requested "
        f"{_money(amount_dec):,.2f} payout "
        f"({_money(ompd_deduction):,.2f} OMPD / {_money(net_release):,.2f} net release)."
    )
    _notify_roles(payout, ["Staff", "Admin"], title, message)
    db.session.commit()
    return payout


def approve_payout_request(payout_id, admin_user_id, note=None):
    payout = db.session.get(PayoutRequest, payout_id)
    if not payout:
        raise ValueError("Payout request not found.")
    if payout.status != PAYOUT_STATUS_PENDING:
        raise ValueError("Only pending payout requests can be approved.")

    now = _now()
    payout.status = PAYOUT_STATUS_APPROVED
    payout.request_reviewed_at = now
    payout.request_reviewed_by_user_id = admin_user_id
    payout.request_review_note = (note or "").strip() or None

    gross, ompd, net = _payout_amounts(payout)
    title = "Payout request approved"
    message = (
        f"Payout #{payout.payout_id} for member #{payout.member_id} "
        f"({_money(gross):,.2f} gross, {_money(net):,.2f} net release) was approved. "
        f"Staff may submit fund release."
    )
    _notify_roles(payout, ["Staff"], title, message)
    _notify_member(
        payout,
        _member_user_id(payout.member_id),
        "Payout request approved",
        (
            f"Your payout request for {_money(gross):,.2f} was approved. "
            f"After {PAYOUT_OMPD_PERCENT}% OMPD ({_money(ompd):,.2f}), "
            f"{_money(net):,.2f} will be released to you."
        ),
    )
    db.session.commit()
    return payout


def reject_payout_request(payout_id, admin_user_id, reason):
    payout = db.session.get(PayoutRequest, payout_id)
    if not payout:
        raise ValueError("Payout request not found.")
    if payout.status != PAYOUT_STATUS_PENDING:
        raise ValueError("Only pending payout requests can be rejected.")

    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Rejection reason is required.")

    now = _now()
    payout.status = PAYOUT_STATUS_REJECTED
    payout.request_reviewed_at = now
    payout.request_reviewed_by_user_id = admin_user_id
    payout.request_review_note = reason
    payout.rejected_at = now
    payout.rejected_by_user_id = admin_user_id
    payout.rejection_reason = reason

    _notify_member(
        payout,
        _member_user_id(payout.member_id),
        "Payout request rejected",
        f"Your payout request was rejected: {reason}",
    )
    db.session.commit()
    return payout


def _release_method_for_recording(method, other_method=None):
    method = (method or "").strip()
    other_method = (other_method or "").strip()
    if method not in PAYOUT_RELEASE_METHODS:
        raise ValueError("Invalid release method.")
    if method == PAYOUT_RELEASE_METHOD_OTHER:
        if not other_method:
            raise ValueError("Other release method is required.")
        if len(other_method) > 40:
            raise ValueError("Other release method must be 40 characters or fewer.")
        return other_method
    return method


def _release_account_info_for_recording(method, account_info=None, bank_name=None, bank_branch=None):
    account_info = (account_info or "").strip()
    if method != PAYOUT_RELEASE_METHOD_BANK_DEPOSIT:
        return account_info or None

    bank_name = (bank_name or "").strip()
    bank_branch = (bank_branch or "").strip()
    if not bank_name:
        raise ValueError("Bank name is required for bank deposits.")
    if not bank_branch:
        raise ValueError("Bank branch is required for bank deposits.")

    account_parts = []
    if account_info:
        account_parts.append(f"Account: {account_info}")
    account_parts.extend([f"Bank: {bank_name}", f"Branch: {bank_branch}"])
    recorded_info = " | ".join(account_parts)
    if len(recorded_info) > 255:
        raise ValueError("Bank deposit details must be 255 characters or fewer.")
    return recorded_info


def submit_payout_release(
    payout_id,
    staff_user_id,
    method,
    reference,
    account_info=None,
    notes=None,
    other_method=None,
    bank_name=None,
    bank_branch=None,
):
    payout = db.session.get(PayoutRequest, payout_id)
    if not payout:
        raise ValueError("Payout request not found.")
    if payout.status != PAYOUT_STATUS_APPROVED:
        raise ValueError("Fund release can only be submitted for approved payout requests.")

    selected_method = (method or "").strip()
    method = _release_method_for_recording(selected_method, other_method)
    account_info = _release_account_info_for_recording(
        selected_method,
        account_info,
        bank_name,
        bank_branch,
    )
    reference = (reference or "").strip()
    if not reference:
        raise ValueError("Release reference is required.")

    now = _now()
    payout.status = PAYOUT_STATUS_RELEASE_SUBMITTED
    payout.release_method = method
    payout.release_reference = reference
    payout.release_account_info = account_info
    payout.release_notes = (notes or "").strip() or None
    payout.release_submitted_at = now
    payout.release_submitted_by_user_id = staff_user_id

    gross, ompd, net = _payout_amounts(payout)
    title = "Fund release submitted"
    message = (
        f"Payout #{payout.payout_id} net release {_money(net):,.2f} via {method} "
        f"(Ref: {reference}) awaits admin approval."
    )
    _notify_roles(payout, ["Admin"], title, message)
    db.session.commit()
    return payout


def reject_payout_release(payout_id, admin_user_id, reason):
    payout = db.session.get(PayoutRequest, payout_id)
    if not payout:
        raise ValueError("Payout request not found.")
    if payout.status != PAYOUT_STATUS_RELEASE_SUBMITTED:
        raise ValueError("Only submitted fund releases can be rejected.")

    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Rejection reason is required.")

    payout.status = PAYOUT_STATUS_APPROVED
    payout.release_approved_at = None
    payout.release_approved_by_user_id = None
    payout.rejection_reason = reason
    payout.rejected_at = _now()
    payout.rejected_by_user_id = admin_user_id

    title = "Fund release rejected"
    message = f"Payout #{payout.payout_id} release was rejected: {reason}. Staff may resubmit."
    _notify_roles(payout, ["Staff"], title, message)
    db.session.commit()
    return payout


def approve_payout_release(payout_id, admin_user_id):
    payout = db.session.get(PayoutRequest, payout_id)
    if not payout:
        raise ValueError("Payout request not found.")
    if payout.status != PAYOUT_STATUS_RELEASE_SUBMITTED:
        raise ValueError("Only submitted fund releases can be approved.")
    if payout.ledger_entry:
        raise ValueError("This payout has already been recorded on the ledger.")
    if payout.ompd_entry:
        raise ValueError("OMPD fund entry already exists for this payout.")

    now = _now()
    gross, ompd, net = _payout_amounts(payout)
    description_parts = [
        "Fund release",
        payout.release_method or "Release",
        f"Net {_money(net):,.2f}",
        f"OMPD {_money(ompd):,.2f}",
        f"Ref: {payout.release_reference}",
    ]
    if payout.release_account_info:
        description_parts.append(payout.release_account_info)

    ledger = MemberLedger(
        member_id=payout.member_id,
        transaction_type=LEDGER_TRANSACTION_DEBIT,
        batch_id=None,
        entry_id=None,
        billing_date=now.date(),
        project_id=None,
        billing_id=None,
        project_title="Fund Release",
        recipient_type="payout",
        share_scheme=None,
        level=0,
        share_amount=gross,
        description=" — ".join(description_parts),
        payout_request_id=payout.payout_id,
        created_at=now,
    )
    db.session.add(ledger)
    db.session.flush()

    db.session.add(OmpdFundEntry(
        payout_id=payout.payout_id,
        member_id=payout.member_id,
        gross_amount=gross,
        deduction_amount=ompd,
        net_released=net,
        release_method=payout.release_method,
        release_reference=payout.release_reference,
        recorded_at=now,
    ))

    payout.status = PAYOUT_STATUS_RELEASED
    payout.release_approved_at = now
    payout.release_approved_by_user_id = admin_user_id
    payout.released_at = now

    title = "Funds released"
    message = (
        f"Payout #{payout.payout_id}: {_money(net):,.2f} released via {payout.release_method} "
        f"({_money(ompd):,.2f} to {OMPD_FUND_LABEL})."
    )
    _notify_roles(payout, ["Staff"], title, message)
    _notify_member(
        payout,
        _member_user_id(payout.member_id),
        "Payout completed",
        (
            f"{_money(net):,.2f} was released via {payout.release_method}. "
            f"{PAYOUT_OMPD_PERCENT}% OMPD ({_money(ompd):,.2f}) was allocated to platform operations."
        ),
    )
    db.session.commit()
    return payout


def payout_queue_counts(role):
    role = (role or "").strip()
    if is_admin_role(role):
        pending = PayoutRequest.query.filter_by(status=PAYOUT_STATUS_PENDING).count()
        release_pending = PayoutRequest.query.filter_by(status=PAYOUT_STATUS_RELEASE_SUBMITTED).count()
        return {
            "pending_requests": pending,
            "pending_releases": release_pending,
            "awaiting_release": 0,
        }
    if role == "Staff":
        awaiting = PayoutRequest.query.filter_by(status=PAYOUT_STATUS_APPROVED).count()
        return {
            "pending_requests": 0,
            "pending_releases": 0,
            "awaiting_release": awaiting,
        }
    return {"pending_requests": 0, "pending_releases": 0, "awaiting_release": 0}


def unread_notification_count(user_id, role):
    query = PayoutNotification.query.filter_by(is_read=False)
    audience_roles = [role]
    if is_admin_role(role):
        audience_roles.append("Admin")
    query = query.filter(
        or_(
            PayoutNotification.user_id == user_id,
            PayoutNotification.audience_role.in_(audience_roles),
        )
    )
    return query.count()


def fund_release_rows(date_from=None, date_to=None, member_id=None, method=None):
    query = payout_request_query(status=PAYOUT_STATUS_RELEASED)
    if member_id:
        query = query.filter(PayoutRequest.member_id == member_id)
    if method:
        query = query.filter(PayoutRequest.release_method == method)
    if date_from:
        query = query.filter(PayoutRequest.released_at >= date_from)
    if date_to:
        query = query.filter(PayoutRequest.released_at <= date_to)
    return [payout_to_dict(row) for row in query.all()]


def fund_release_summary(date_from=None, date_to=None, member_id=None, method=None):
    rows = fund_release_rows(date_from, date_to, member_id, method)
    by_method = {}
    by_member = {}
    total_gross = Decimal("0")
    total_ompd = Decimal("0")
    total_net = Decimal("0")
    for row in rows:
        gross = Decimal(str(row["requested_amount"]))
        ompd = Decimal(str(row["ompd_deduction"]))
        net = Decimal(str(row["net_release_amount"]))
        total_gross += gross
        total_ompd += ompd
        total_net += net
        method_key = row["release_method"] or "Unknown"
        by_method[method_key] = by_method.get(method_key, {
            "gross": Decimal("0"),
            "ompd": Decimal("0"),
            "net": Decimal("0"),
            "count": 0,
        })
        bucket = by_method[method_key]
        bucket["gross"] += gross
        bucket["ompd"] += ompd
        bucket["net"] += net
        bucket["count"] += 1
        member_key = (row["member_id"], row["member_name"])
        by_member[member_key] = by_member.get(member_key, {
            "gross": Decimal("0"),
            "ompd": Decimal("0"),
            "net": Decimal("0"),
            "count": 0,
        })
        member_bucket = by_member[member_key]
        member_bucket["gross"] += gross
        member_bucket["ompd"] += ompd
        member_bucket["net"] += net
        member_bucket["count"] += 1

    return {
        "release_count": len(rows),
        "total_gross": _money(total_gross),
        "total_ompd": _money(total_ompd),
        "total_released": _money(total_net),
        "total_net_released": _money(total_net),
        "ompd_percent": PAYOUT_OMPD_PERCENT,
        "by_method": [
            {
                "method": key,
                "total": _money(value["net"]),
                "total_gross": _money(value["gross"]),
                "total_ompd": _money(value["ompd"]),
                "count": value["count"],
            }
            for key, value in sorted(by_method.items(), key=lambda item: item[0])
        ],
        "by_member": [
            {
                "member_id": key[0],
                "member_name": key[1],
                "total": _money(value["net"]),
                "total_gross": _money(value["gross"]),
                "total_ompd": _money(value["ompd"]),
                "count": value["count"],
            }
            for key, value in sorted(by_member.items(), key=lambda item: item[0][1])
        ],
    }


def ompd_fund_query(date_from=None, date_to=None, member_id=None):
    query = (
        OmpdFundEntry.query
        .options(joinedload(OmpdFundEntry.member), joinedload(OmpdFundEntry.payout))
        .order_by(OmpdFundEntry.recorded_at.desc(), OmpdFundEntry.entry_id.desc())
    )
    if member_id:
        query = query.filter(OmpdFundEntry.member_id == member_id)
    if date_from:
        query = query.filter(OmpdFundEntry.recorded_at >= date_from)
    if date_to:
        query = query.filter(OmpdFundEntry.recorded_at <= date_to)
    return query


def ompd_entry_to_dict(entry):
    return {
        "entry_id": entry.entry_id,
        "payout_id": entry.payout_id,
        "member_id": entry.member_id,
        "member_name": _member_name(entry.member),
        "gross_amount": _money(entry.gross_amount),
        "deduction_amount": _money(entry.deduction_amount),
        "net_released": _money(entry.net_released),
        "release_method": entry.release_method or "",
        "release_reference": entry.release_reference or "",
        "recorded_at": entry.recorded_at.isoformat() if entry.recorded_at else None,
    }


def ompd_fund_summary(date_from=None, date_to=None, member_id=None):
    query = ompd_fund_query(date_from, date_to, member_id)
    entries = query.all()
    total_ompd = sum(Decimal(str(entry.deduction_amount or 0)) for entry in entries)
    total_gross = sum(Decimal(str(entry.gross_amount or 0)) for entry in entries)
    total_net = sum(Decimal(str(entry.net_released or 0)) for entry in entries)
    return {
        "entry_count": len(entries),
        "total_ompd": _money(total_ompd),
        "total_gross": _money(total_gross),
        "total_net_released": _money(total_net),
        "ompd_percent": PAYOUT_OMPD_PERCENT,
        "scheme": payout_scheme_summary(),
    }


def ompd_fund_rows(date_from=None, date_to=None, member_id=None, limit=None):
    query = ompd_fund_query(date_from, date_to, member_id)
    if limit:
        query = query.limit(limit)
    return [ompd_entry_to_dict(entry) for entry in query.all()]
