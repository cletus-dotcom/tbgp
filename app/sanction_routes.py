"""Member suspensions page: issue, review, and lift policy sanctions."""

from flask import abort, flash, redirect, render_template, request, url_for

from app import db
from app.auth import login_required, staff_or_admin_required
from app.config import SANCTION_DEFAULT_DAYS, SANCTION_MAX_DAYS, can_manage_sanctions, normalize_role
from app.models import Member
from app.routes import _dashboard_user, main_routes
from app.sanction_service import (
    SANCTION_STATUS_LABELS,
    format_day,
    get_sanction,
    issue_sanction,
    lift_sanction,
    list_sanctions,
)
from app.timeutil import manila_today


@main_routes.route("/members/suspensions", methods=["GET", "POST"])
@login_required
@staff_or_admin_required
def member_suspensions():
    user = _dashboard_user()
    if request.method == "POST":
        if not can_manage_sanctions(user.role):
            abort(403)
        action = (request.form.get("action") or "").strip()
        try:
            if action == "issue":
                raw_member = (request.form.get("member_id") or "").strip()
                sanction = issue_sanction(
                    int(raw_member) if raw_member.isdigit() else None,
                    request.form.get("reason"),
                    user,
                    memo_number=request.form.get("memo_number"),
                    start_date=request.form.get("start_date"),
                    days=request.form.get("days"),
                    blocks_ads=request.form.get("blocks_ads") == "1",
                    blocks_endorsement=request.form.get("blocks_endorsement") == "1",
                )
                flash(
                    f"{sanction.member.full_name} is suspended from {', '.join(sanction.scope_labels).lower()} "
                    f"from {format_day(sanction.start_date)} to {format_day(sanction.end_date)}.",
                    "success",
                )
            elif action == "lift":
                raw_id = (request.form.get("sanction_id") or "").strip()
                sanction = get_sanction(int(raw_id)) if raw_id.isdigit() else None
                if sanction is None:
                    raise ValueError("Suspension not found.")
                lift_sanction(sanction, request.form.get("lift_reason"), user)
                flash(f"Suspension of {sanction.member.full_name} lifted.", "success")
            else:
                raise ValueError("Unknown action.")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        return redirect(url_for("main_routes.member_suspensions"))

    today = manila_today()
    sanctions = list_sanctions()
    violation_counts = {}
    for sanction in sanctions:
        violation_counts[sanction.member_id] = violation_counts.get(sanction.member_id, 0) + 1
    return render_template(
        "member_suspensions.html",
        fullname=user.full_name or "User",
        role=normalize_role(user.role),
        active_page="member_suspensions",
        sanctions=sanctions,
        active_sanctions=[s for s in sanctions if s.status_on(today) in ("active", "scheduled")],
        past_sanctions=[s for s in sanctions if s.status_on(today) in ("served", "lifted")],
        violation_counts=violation_counts,
        status_labels=SANCTION_STATUS_LABELS,
        members=Member.query.filter(Member.status == "Active")
        .order_by(Member.last_name.asc(), Member.first_name.asc())
        .all(),
        can_manage=can_manage_sanctions(user.role),
        today=today,
        default_days=SANCTION_DEFAULT_DAYS,
        max_days=SANCTION_MAX_DAYS,
        format_day=format_day,
    )
