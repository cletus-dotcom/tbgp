from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.config import (
    ADMIN_ACCOUNT_PERCENT,
    ADMIN_MEMBER_ID,
    ADMIN_RECIPIENT_LABEL,
    ADMIN_SHARING_LEVEL,
    CLIENT_POOL_PERCENT,
    COMMISSION_SCHEME_CLIENT,
    COMMISSION_SCHEME_CONTRACTOR,
    COMMISSION_SCHEME_PLATFORM_POP,
    COMMISSION_SCHEME_PLATFORM_REF_CLIENT,
    COMMISSION_SCHEME_PLATFORM_REF_CONTRACTOR,
    CONTRACTOR_POOL_PERCENT,
    MAX_SHARING_LEVELS,
    MEMBER_EARNINGS_CAP_FIRST_PROJECT,
    MEMBER_EARNINGS_CAP_NTH_PROJECT,
    MEMBER_EARNINGS_CAP_SECOND_PROJECT,
    MEMBER_LIFETIME_PROJECT_CAP_AFTER_LIMIT,
    POP_CAP_FLUSH_LABEL,
    POP_LIFETIME_LIMIT_FUND_LABEL,
    POP_RECIPIENT_LABEL,
    mandate_subaccount_label,
)
from app.ledger_service import delete_sharing_batch, record_ledger_for_batch
from app.models import (
    CommissionLevel,
    Member,
    ProjectBilling,
    ProjectCommission,
    SharingBatch,
    SharingEntry,
)


def get_commission_levels(scheme=COMMISSION_SCHEME_CLIENT):
    return (
        CommissionLevel.query
        .filter_by(scheme=scheme)
        .order_by(CommissionLevel.level.asc())
        .all()
    )


def get_level_percentage_map(scheme):
    levels = get_commission_levels(scheme)
    if len(levels) < MAX_SHARING_LEVELS:
        scheme_label = "Ref-Client" if scheme == COMMISSION_SCHEME_CLIENT else "Ref-Contractor"
        raise ValueError(
            f"{scheme_label} commission scheme requires {MAX_SHARING_LEVELS} levels. "
            "Configure all levels under Commission Management."
        )
    level_map = {item.level: Decimal(str(item.percentage)) for item in levels}
    total = sum(level_map.values())
    if total != Decimal("100"):
        scheme_label = "Ref-Client" if scheme == COMMISSION_SCHEME_CLIENT else "Ref-Contractor"
        raise ValueError(
            f"{scheme_label} commission levels must total 100% (currently {total}). "
            "Update percentages under Commission Management."
        )
    return level_map


def get_admin_member():
    if not ADMIN_MEMBER_ID:
        return None
    try:
        member_id = int(ADMIN_MEMBER_ID)
    except (TypeError, ValueError):
        return None
    member = db.session.get(Member, member_id)
    if member and member.status == "Active":
        return member
    return None


def _quantize_money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _commission_gross(commission_amount):
    return Decimal(str(commission_amount or 0))


def _portion_amount(commission_amount, percent):
    gross = _commission_gross(commission_amount)
    return _quantize_money(gross * Decimal(str(percent)) / Decimal("100"))


def _share_from_pool(pool, percentage):
    return _quantize_money(pool * percentage / Decimal("100"))


def _next_active_referrer(member):
    current = member.referrer
    while current and current.status != "Active":
        current = current.referrer
    return current


def build_sharing_chain(referrer_id):
    chain = []
    current = db.session.get(Member, referrer_id)
    if not current or current.status != "Active":
        return chain

    chain.append(current)
    while len(chain) < MAX_SHARING_LEVELS:
        nxt = _next_active_referrer(current)
        if not nxt:
            break
        chain.append(nxt)
        current = nxt
    return chain


def _pop_label(share_scheme):
    if share_scheme == COMMISSION_SCHEME_CLIENT:
        return f"{POP_RECIPIENT_LABEL} (Ref-Client)"
    if share_scheme == COMMISSION_SCHEME_PLATFORM_REF_CLIENT:
        return f"{POP_RECIPIENT_LABEL} (Platform Ref-Client)"
    return f"{POP_RECIPIENT_LABEL} (Ref-Contractor)"


def _entry(project, billing, member, recipient_type, recipient_label, level, percentage, share_amount, share_scheme):
    return {
        "project": project,
        "billing": billing,
        "member": member,
        "recipient_type": recipient_type,
        "recipient_label": recipient_label,
        "share_scheme": share_scheme,
        "level": level,
        "percentage": percentage,
        "share_amount": share_amount,
    }


def _cap_for_member_project_number(project_number):
    if project_number <= 1:
        return MEMBER_EARNINGS_CAP_FIRST_PROJECT
    if project_number == 2:
        return MEMBER_EARNINGS_CAP_SECOND_PROJECT
    return MEMBER_EARNINGS_CAP_NTH_PROJECT


def _load_member_project_counts():
    rows = (
        db.session.query(
            SharingEntry.member_id,
            func.count(func.distinct(SharingEntry.project_id)),
        )
        .filter(
            SharingEntry.member_id.isnot(None),
            SharingEntry.recipient_type == "member",
            SharingEntry.share_amount > 0,
        )
        .group_by(SharingEntry.member_id)
        .all()
    )
    return {member_id: int(count) for member_id, count in rows}


def _load_member_lifetime_earnings():
    rows = (
        db.session.query(
            SharingEntry.member_id,
            func.coalesce(func.sum(SharingEntry.share_amount), 0),
        )
        .filter(
            SharingEntry.member_id.isnot(None),
            SharingEntry.recipient_type == "member",
            SharingEntry.share_amount > 0,
        )
        .group_by(SharingEntry.member_id)
        .all()
    )
    return {member_id: _quantize_money(total) for member_id, total in rows}


def _member_earning_entries(entries):
    return [
        entry for entry in entries
        if entry["recipient_type"] == "member" and entry["member"]
    ]


def _apply_member_earnings_caps(project_entries, member_project_counts):
    """Cap per-member earnings for one project; overflow goes to POP."""
    cap_flush_entries = []
    by_member = {}
    for entry in _member_earning_entries(project_entries):
        member_id = entry["member"].member_id
        by_member.setdefault(member_id, []).append(entry)

    for member_id, member_entries in by_member.items():
        project_number = member_project_counts.get(member_id, 0) + 1
        cap = _cap_for_member_project_number(project_number)
        total = sum(entry["share_amount"] for entry in member_entries)
        if total > cap:
            overflow = _quantize_money(total - cap)
            ratio = cap / total
            for entry in member_entries:
                entry["share_amount"] = _quantize_money(entry["share_amount"] * ratio)
            cap_flush_entries.append(_entry(
                member_entries[0]["project"],
                member_entries[0]["billing"],
                None,
                "pop",
                POP_CAP_FLUSH_LABEL,
                0,
                Decimal("0"),
                overflow,
                member_entries[0]["share_scheme"],
            ))

        member_project_counts[member_id] = project_number

    return cap_flush_entries


def _lifetime_project_allowance(earned, threshold, project_total):
    """Allow normal earnings until threshold, then a smaller per-project cap."""
    if earned >= threshold:
        return min(project_total, MEMBER_LIFETIME_PROJECT_CAP_AFTER_LIMIT)

    threshold_remaining = max(Decimal("0"), threshold - earned)
    if project_total <= threshold_remaining:
        return project_total

    return min(project_total, threshold_remaining + MEMBER_LIFETIME_PROJECT_CAP_AFTER_LIMIT)


def _apply_member_lifetime_caps(project_entries, lifetime_earnings):
    """Apply post-lifetime-limit project caps; overflow goes to POP lifetime fund."""
    cap_flush_entries = []
    by_member = {}
    for entry in _member_earning_entries(project_entries):
        member_id = entry["member"].member_id
        by_member.setdefault(member_id, []).append(entry)

    for member_id, member_entries in by_member.items():
        member = member_entries[0]["member"]
        if not member.lifetime_cap_enabled:
            lifetime_earnings[member_id] = lifetime_earnings.get(member_id, Decimal("0")) + sum(
                entry["share_amount"] for entry in member_entries
            )
            continue

        cap = Decimal(str(member.lifetime_cap_amount or 0))
        earned = lifetime_earnings.get(member_id, Decimal("0"))
        total = sum(entry["share_amount"] for entry in member_entries)
        allowance = _quantize_money(_lifetime_project_allowance(earned, cap, total))
        if total > allowance:
            overflow = _quantize_money(total - allowance)
            ratio = Decimal("0") if allowance <= 0 else allowance / total
            for entry in member_entries:
                entry["share_amount"] = _quantize_money(entry["share_amount"] * ratio)
            cap_flush_entries.append(_entry(
                member_entries[0]["project"],
                member_entries[0]["billing"],
                None,
                "pop",
                POP_LIFETIME_LIMIT_FUND_LABEL,
                0,
                Decimal("0"),
                overflow,
                member_entries[0]["share_scheme"],
            ))
            total = allowance

        lifetime_earnings[member_id] = earned + total

    return cap_flush_entries


def _summarize_entries(entries):
    total_admin = Decimal("0")
    total_shared = Decimal("0")
    total_pop = Decimal("0")
    total_mandate = Decimal("0")
    for entry in entries:
        amount = entry["share_amount"]
        recipient_type = entry["recipient_type"]
        if recipient_type == "admin":
            total_admin += amount
        elif recipient_type == "pop":
            total_pop += amount
        elif recipient_type == "mandate":
            total_mandate += amount
        else:
            total_shared += amount
    return total_admin, total_shared, total_pop, total_mandate


def _distribute_referrer_pool(project, billing, referrer_id, level_map, pool, share_scheme):
    entries = []
    if pool <= 0:
        return entries, Decimal("0"), Decimal("0")

    pop_pct = Decimal("0")

    if not referrer_id:
        pop_pct = sum(level_map.get(slot, Decimal("0")) for slot in range(1, MAX_SHARING_LEVELS + 1))
    else:
        chain = build_sharing_chain(referrer_id)

        for slot in range(1, MAX_SHARING_LEVELS):
            pct = level_map.get(slot, Decimal("0"))
            if pct <= 0:
                continue

            if slot > len(chain):
                pop_pct += pct
                continue

            member = chain[slot - 1]
            amount = _share_from_pool(pool, pct)
            entries.append(_entry(
                project, billing, member, "member", None, slot, pct, amount, share_scheme,
            ))
        else:
            mandate_pct = level_map.get(MAX_SHARING_LEVELS, Decimal("0"))
            if mandate_pct > 0:
                mandate_amount = _share_from_pool(pool, mandate_pct)
                entries.append(_entry(
                    project,
                    billing,
                    None,
                    "mandate",
                    mandate_subaccount_label(share_scheme),
                    MAX_SHARING_LEVELS,
                    mandate_pct,
                    mandate_amount,
                    share_scheme,
                ))

    if pop_pct > 0:
        pop_amount = _share_from_pool(pool, pop_pct)
        entries.append(_entry(
            project,
            billing,
            None,
            "pop",
            _pop_label(share_scheme),
            0,
            pop_pct,
            pop_amount,
            share_scheme,
        ))

    total_shared = sum(
        item["share_amount"] for item in entries if item["recipient_type"] == "member"
    )
    total_pop = sum(item["share_amount"] for item in entries if item["recipient_type"] == "pop")
    return entries, total_shared, total_pop


def _admin_entry(project, billing, admin_member):
    amount = _portion_amount(billing.billing_amount, ADMIN_ACCOUNT_PERCENT)
    if amount <= 0:
        return None
    return _entry(
        project,
        billing,
        admin_member,
        "admin",
        ADMIN_RECIPIENT_LABEL,
        ADMIN_SHARING_LEVEL,
        Decimal(str(ADMIN_ACCOUNT_PERCENT)),
        amount,
        None,
    )

def _platform_entries(
    project,
    billing,
    platform_member,
    client_level_map,
    contractor_level_map,
):
    """
    Split the PLATFORM pool (ADMIN_ACCOUNT_PERCENT) into sub-accounts:

    - 5%  founders_prerogative      -> credited to PLATFORM account (separate entry label)
    - 12% platform_ref_client       -> distributed like Ref-Client MLM and credited to member ledgers
    - 8%  platform_ref_contractor   -> distributed like Ref-Contractor MLM and credited to member ledgers
    - 10% platform_POP              -> goes to POP
    - 65% platform                  -> credited to PLATFORM account (separate entry label)
    """
    platform_pool = _portion_amount(billing.billing_amount, ADMIN_ACCOUNT_PERCENT)
    if platform_pool <= 0:
        return [], Decimal("0"), Decimal("0")

    founders = _quantize_money(platform_pool * Decimal("0.05"))
    plat_client = _quantize_money(platform_pool * Decimal("0.12"))
    plat_contractor = _quantize_money(platform_pool * Decimal("0.08"))
    plat_pop = _quantize_money(platform_pool * Decimal("0.10"))
    plat_main = _quantize_money(platform_pool - founders - plat_client - plat_contractor - plat_pop)

    entries = []

    # PLATFORM account entries (still stored as recipient_type='admin' for compatibility)
    if platform_member and founders > 0:
        entries.append(_entry(
            project,
            billing,
            platform_member,
            "admin",
            f"{ADMIN_RECIPIENT_LABEL} — founders_prerogative",
            ADMIN_SHARING_LEVEL,
            Decimal("5.00"),
            founders,
            None,
        ))

    if platform_member and plat_main > 0:
        entries.append(_entry(
            project,
            billing,
            platform_member,
            "admin",
            f"{ADMIN_RECIPIENT_LABEL} — platform",
            ADMIN_SHARING_LEVEL,
            Decimal("65.00"),
            plat_main,
            None,
        ))

    # Platform POP sub-account
    if plat_pop > 0:
        entries.append(_entry(
            project,
            billing,
            None,
            "pop",
            f"{POP_RECIPIENT_LABEL} (Platform)",
            0,
            Decimal("10.00"),
            plat_pop,
            COMMISSION_SCHEME_PLATFORM_POP,
        ))

    # Platform Ref-Client sub-account (distributed like Ref-Client MLM)
    plat_client_entries, _, plat_client_pop = _distribute_referrer_pool(
        project,
        billing,
        project.client_referrer_id,
        client_level_map,
        plat_client,
        COMMISSION_SCHEME_PLATFORM_REF_CLIENT,
    )
    entries.extend(plat_client_entries)

    plat_contractor_entries, _, plat_contractor_pop = _distribute_referrer_pool(
        project,
        billing,
        project.contractor_referrer_id,
        contractor_level_map,
        plat_contractor,
        COMMISSION_SCHEME_PLATFORM_REF_CONTRACTOR,
    )
    entries.extend(plat_contractor_entries)

    # Note: any unfilled/upline POP from the platform ref pools are already created by _distribute_referrer_pool
    # (plat_client_pop / plat_contractor_pop are included inside entries).
    platform_pop_total = plat_pop + plat_client_pop + plat_contractor_pop
    platform_shared_total = founders + plat_main + (plat_client - plat_client_pop) + (plat_contractor - plat_contractor_pop)

    return entries, platform_shared_total, platform_pop_total


def distribute_billing_shares(
    project,
    billing,
    client_level_map,
    contractor_level_map,
    admin_member=None,
):
    entries = []
    platform_entries, platform_shared, platform_pop = _platform_entries(
        project,
        billing,
        admin_member,
        client_level_map,
        contractor_level_map,
    )
    entries.extend(platform_entries)

    client_pool = _portion_amount(billing.billing_amount, CLIENT_POOL_PERCENT)
    contractor_pool = _portion_amount(billing.billing_amount, CONTRACTOR_POOL_PERCENT)

    client_entries, client_shared, client_pop = _distribute_referrer_pool(
        project,
        billing,
        project.client_referrer_id,
        client_level_map,
        client_pool,
        COMMISSION_SCHEME_CLIENT,
    )
    contractor_entries, contractor_shared, contractor_pop = _distribute_referrer_pool(
        project,
        billing,
        project.contractor_referrer_id,
        contractor_level_map,
        contractor_pool,
        COMMISSION_SCHEME_CONTRACTOR,
    )
    entries.extend(client_entries)
    entries.extend(contractor_entries)

    total_admin = platform_shared
    total_shared = client_shared + contractor_shared
    total_pop = client_pop + contractor_pop + platform_pop

    return entries, client_pool, contractor_pool, total_admin, total_shared, total_pop


def billings_for_billing_date(billing_date):
    return (
        ProjectBilling.query
        .join(ProjectCommission)
        .options(
            joinedload(ProjectBilling.project).joinedload(ProjectCommission.contractor),
        )
        .filter(ProjectBilling.billing_date == billing_date)
        .order_by(ProjectCommission.project_id.asc(), ProjectBilling.billing_id.asc())
        .all()
    )


def generated_billing_dates():
    rows = (
        db.session.query(SharingBatch.commission_date)
        .distinct()
        .order_by(SharingBatch.commission_date.desc())
        .all()
    )
    return [row[0] for row in rows]


def is_billing_date_generated(billing_date):
    return (
        SharingBatch.query
        .filter(SharingBatch.commission_date == billing_date)
        .first()
        is not None
    )


def ungenerated_billing_dates():
    all_dates = set(billing_dates_with_billings())
    generated = set(generated_billing_dates())
    return sorted(all_dates - generated, reverse=True)


def billing_dates_with_billings():
    rows = (
        db.session.query(ProjectBilling.billing_date)
        .filter(ProjectBilling.billing_date.isnot(None))
        .distinct()
        .order_by(ProjectBilling.billing_date.desc())
        .all()
    )
    return [row[0] for row in rows]


# Backward-compatible aliases used by routes/templates
commission_dates_with_projects = billing_dates_with_billings


def projects_for_commission_date(billing_date):
    return billings_for_billing_date(billing_date)


def generate_profit_sharing(billing_date):
    total_percent = CLIENT_POOL_PERCENT + CONTRACTOR_POOL_PERCENT + ADMIN_ACCOUNT_PERCENT
    if total_percent != 100:
        raise ValueError(
            f"Commission split must total 100% "
            f"(Ref-Client {CLIENT_POOL_PERCENT}% + Ref-Contractor {CONTRACTOR_POOL_PERCENT}% "
            f"+ PLATFORM {ADMIN_ACCOUNT_PERCENT}% = {total_percent}%)."
        )

    client_level_map = get_level_percentage_map(COMMISSION_SCHEME_CLIENT)
    contractor_level_map = get_level_percentage_map(COMMISSION_SCHEME_CONTRACTOR)

    admin_member = get_admin_member()
    if is_billing_date_generated(billing_date):
        raise ValueError(
            f"Sharing already generated for billing date {billing_date.isoformat()}. "
            "Delete the existing batch from history to regenerate."
        )

    billings = billings_for_billing_date(billing_date)
    if not billings:
        raise ValueError(f"No project billings found for billing date {billing_date.isoformat()}.")

    member_project_counts = _load_member_project_counts()
    lifetime_earnings = _load_member_lifetime_earnings()
    all_entries = []
    total_commission = Decimal("0")
    total_client_pool = Decimal("0")
    total_contractor_pool = Decimal("0")

    for billing in billings:
        project = billing.project
        total_commission += Decimal(str(billing.billing_amount or 0))
        entries, client_pool, contractor_pool, _, _, _ = distribute_billing_shares(
            project,
            billing,
            client_level_map,
            contractor_level_map,
            admin_member,
        )
        total_client_pool += client_pool
        total_contractor_pool += contractor_pool
        cap_flush_entries = _apply_member_earnings_caps(entries, member_project_counts)
        entries.extend(cap_flush_entries)
        lifetime_flush_entries = _apply_member_lifetime_caps(entries, lifetime_earnings)
        entries.extend(lifetime_flush_entries)
        all_entries.extend(entries)

    total_admin, total_shared, total_pop, total_mandate = _summarize_entries(all_entries)

    batch = SharingBatch(
        commission_date=billing_date,
        generated_at=datetime.utcnow(),
        project_count=len(billings),
        total_commission=total_commission,
        total_client_pool=total_client_pool,
        total_contractor_pool=total_contractor_pool,
        total_pool=total_client_pool + total_contractor_pool,
        total_admin=total_admin,
        total_shared=total_shared,
        total_pop=total_pop,
    )
    db.session.add(batch)
    db.session.flush()

    for item in all_entries:
        db.session.add(SharingEntry(
            batch_id=batch.batch_id,
            project_id=item["project"].project_id,
            billing_id=item["billing"].billing_id if item.get("billing") else None,
            member_id=item["member"].member_id if item["member"] else None,
            recipient_type=item["recipient_type"],
            recipient_label=item["recipient_label"],
            share_scheme=item["share_scheme"],
            level=item["level"],
            percentage=item["percentage"],
            share_amount=item["share_amount"],
        ))

    record_ledger_for_batch(batch)
    db.session.commit()
    return batch


def remove_sharing_batch(batch_id):
    return delete_sharing_batch(batch_id)


def sharing_batch_summary(batch):
    entries = (
        SharingEntry.query
        .filter_by(batch_id=batch.batch_id)
        .order_by(
            SharingEntry.project_id.asc(),
            SharingEntry.share_scheme.asc(),
            SharingEntry.level.asc(),
            SharingEntry.entry_id.asc(),
        )
        .all()
    )
    return {
        "batch_id": batch.batch_id,
        "commission_date": batch.commission_date.isoformat(),
        "generated_at": batch.generated_at.isoformat(),
        "project_count": batch.project_count,
        "total_commission": float(batch.total_commission or 0),
        "total_client_pool": float(batch.total_client_pool or 0),
        "total_contractor_pool": float(batch.total_contractor_pool or 0),
        "total_pool": float(batch.total_pool or 0),
        "total_admin": float(batch.total_admin or 0),
        "total_shared": float(batch.total_shared or 0),
        "total_pop": float(batch.total_pop or 0),
        "client_pool_percent": CLIENT_POOL_PERCENT,
        "contractor_pool_percent": CONTRACTOR_POOL_PERCENT,
        "admin_account_percent": ADMIN_ACCOUNT_PERCENT,
        "member_earnings_caps": {
            "first_project": float(MEMBER_EARNINGS_CAP_FIRST_PROJECT),
            "second_project": float(MEMBER_EARNINGS_CAP_SECOND_PROJECT),
            "nth_project": float(MEMBER_EARNINGS_CAP_NTH_PROJECT),
        },
        "entries": [
            {
                "entry_id": e.entry_id,
                "project_id": e.project_id,
                "project_title": e.project.project_title if e.project else None,
                "billing_id": e.billing_id,
                "billing_date": (
                    e.billing.billing_date.isoformat()
                    if e.billing and e.billing.billing_date
                    else None
                ),
                "billing_amount": float(e.billing.billing_amount or 0) if e.billing else None,
                "member_id": e.member_id,
                "member_name": (
                    e.recipient_label
                    if e.recipient_type in ("pop", "mandate", "admin") and not e.member
                    else (e.member.full_name if e.member else e.recipient_label)
                ),
                "is_cap_flush": e.recipient_type == "pop" and e.recipient_label == POP_CAP_FLUSH_LABEL,
                "recipient_type": e.recipient_type,
                "share_scheme": e.share_scheme,
                "level": e.level,
                "percentage": float(e.percentage or 0),
                "share_amount": float(e.share_amount or 0),
            }
            for e in entries
        ],
    }
