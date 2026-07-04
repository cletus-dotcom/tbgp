from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.config import (
    ADMIN_ACCOUNT_PERCENT,
    ADMIN_RECIPIENT_LABEL,
    CLIENT_POOL_PERCENT,
    COMMISSION_SCHEME_CLIENT,
    COMMISSION_SCHEME_CONTRACTOR,
    CONTRACTOR_POOL_PERCENT,
    DEFAULT_CLIENT_COMMISSION_LEVELS,
    DEFAULT_CONTRACTOR_COMMISSION_LEVELS,
    MANDATE_RECIPIENT_LABEL,
    MANDATE_SUBACCOUNT_LABELS,
    MAX_SHARING_LEVELS,
    POP_CAP_FLUSH_LABEL,
    POP_RECIPIENT_LABEL,
)
from app.models import ProjectBilling, ProjectCommission, SharingBatch, SharingEntry
from app.prof_sharing_service import (
    build_sharing_chain,
    get_commission_levels,
)


def _money(value):
    return round(float(value or 0), 2)


def _account_type_label(entry):
    if entry.recipient_type == "pop":
        return "POP"
    if entry.recipient_type == "admin":
        return "PLATFORM"
    if entry.recipient_type == "mandate":
        return "Mandate"
    return "Member"


def _row_account_type(row):
    if row["recipient_type"] == "pop":
        return "POP"
    if row["recipient_type"] == "admin":
        return "PLATFORM"
    if row["recipient_type"] == "mandate":
        return "Mandate"
    return "Member"


def _recipient_bucket_key(row):
    if row["recipient_type"] == "pop":
        return ("pop", 0, POP_RECIPIENT_LABEL)
    if row["recipient_type"] == "admin":
        member_id = row.get("member_id") or 0
        name = row.get("member_name") or "PLATFORM Account"
        return ("admin", member_id, name)
    member_id = row.get("member_id") or 0
    name = row.get("member_name") or "—"
    return ("member", member_id, name)


def summarize_recipient_totals(entry_rows):
    buckets = defaultdict(lambda: {
        "recipient_kind": "",
        "member_id": None,
        "account_name": "",
        "account_type": "",
        "transaction_count": 0,
        "client_share": Decimal("0"),
        "contractor_share": Decimal("0"),
        "total_share": Decimal("0"),
        "search_text": "",
    })

    for row in entry_rows:
        kind, member_id, name = _recipient_bucket_key(row)
        key = (kind, member_id, name)
        bucket = buckets[key]
        bucket["recipient_kind"] = kind
        bucket["member_id"] = member_id if member_id else None
        bucket["account_name"] = name
        bucket["account_type"] = _row_account_type(row)
        bucket["transaction_count"] += 1
        amount = Decimal(str(row.get("share_amount") or 0))
        bucket["total_share"] += amount
        scheme = row.get("share_scheme")
        if scheme in ("client", "platform_ref_client"):
            bucket["client_share"] += amount
        elif scheme in ("contractor", "platform_ref_contractor"):
            bucket["contractor_share"] += amount

    summary = []
    for bucket in buckets.values():
        bucket["client_share"] = _money(bucket["client_share"])
        bucket["contractor_share"] = _money(bucket["contractor_share"])
        bucket["total_share"] = _money(bucket["total_share"])
        search_parts = [
            bucket["account_name"],
            bucket["account_type"],
            str(bucket["member_id"] or ""),
        ]
        bucket["search_text"] = " ".join(search_parts).lower()
        summary.append(bucket)

    summary.sort(key=lambda row: (-row["total_share"], row["account_name"]))
    grand_total = _money(sum(row["total_share"] for row in summary))
    return {
        "rows": summary,
        "grand_total": grand_total,
        "account_count": len(summary),
    }


def _entry_row(entry):
    member = entry.member
    scheme_label = "—"
    if entry.share_scheme == "client":
        scheme_label = "Ref-Client"
    elif entry.share_scheme == "platform_ref_client":
        scheme_label = "Platform Ref-Client"
    elif entry.share_scheme == "contractor":
        scheme_label = "Ref-Contractor"
    elif entry.share_scheme == "platform_ref_contractor":
        scheme_label = "Platform Ref-Contractor"
    elif entry.share_scheme == "platform_pop":
        scheme_label = "Platform POP"
    elif entry.recipient_type == "admin":
        scheme_label = "PLATFORM"

    level_label = "POP"
    if entry.level == -1:
        level_label = "PLATFORM"
    elif entry.level:
        level_label = f"L{entry.level}"

    return {
        "entry_id": entry.entry_id,
        "scheme_label": scheme_label,
        "share_scheme": entry.share_scheme,
        "recipient_type": entry.recipient_type,
        "member_id": entry.member_id,
        "member_name": member.full_name if member else (entry.recipient_label or "—"),
        "account_type": _account_type_label(entry),
        "level_label": level_label,
        "level": entry.level,
        "percentage": _money(entry.percentage),
        "share_amount": _money(entry.share_amount),
        "recipient_label": entry.recipient_label,
    }


def _project_billing_totals():
    rows = (
        db.session.query(
            SharingEntry.project_id,
            SharingEntry.billing_id,
            ProjectBilling.billing_amount,
        )
        .join(ProjectBilling, SharingEntry.billing_id == ProjectBilling.billing_id)
        .distinct(SharingEntry.project_id, SharingEntry.billing_id)
        .all()
    )
    totals = defaultdict(lambda: Decimal("0"))
    for project_id, _billing_id, amount in rows:
        totals[project_id] += Decimal(str(amount or 0))
    return {pid: _money(total) for pid, total in totals.items()}


def _project_generation_counts():
    batch_counts = dict(
        db.session.query(
            SharingEntry.project_id,
            func.count(func.distinct(SharingEntry.batch_id)),
        )
        .group_by(SharingEntry.project_id)
        .all()
    )
    billing_counts = dict(
        db.session.query(
            SharingEntry.project_id,
            func.count(func.distinct(SharingEntry.billing_id)),
        )
        .group_by(SharingEntry.project_id)
        .all()
    )
    return batch_counts, billing_counts


def generated_projects_index():
    project_ids = [
        row[0]
        for row in (
            db.session.query(SharingEntry.project_id)
            .distinct()
            .order_by(SharingEntry.project_id.desc())
            .all()
        )
    ]
    if not project_ids:
        return []

    projects = (
        ProjectCommission.query
        .options(
            joinedload(ProjectCommission.contractor),
            joinedload(ProjectCommission.client_referrer),
            joinedload(ProjectCommission.contractor_referrer),
        )
        .filter(ProjectCommission.project_id.in_(project_ids))
        .order_by(ProjectCommission.project_title.asc())
        .all()
    )

    billing_totals = _project_billing_totals()
    batch_counts, billing_counts = _project_generation_counts()

    items = []
    for project in projects:
        contractor = project.contractor
        items.append({
            "project_id": project.project_id,
            "project_title": project.project_title,
            "address": project.address,
            "contractor_name": contractor.company_name if contractor else "—",
            "client_referrer_label": ProjectCommission.member_referral_label(project.client_referrer),
            "contractor_referrer_label": ProjectCommission.member_referral_label(project.contractor_referrer),
            "client_referrer_id": project.client_referrer_id,
            "contractor_referrer_id": project.contractor_referrer_id,
            "generation_count": int(batch_counts.get(project.project_id, 0)),
            "billing_count": int(billing_counts.get(project.project_id, 0)),
            "total_commission": billing_totals.get(project.project_id, 0),
            "search_text": " ".join(filter(None, [
                str(project.project_id),
                project.project_title,
                project.address or "",
                contractor.company_name if contractor else "",
                ProjectCommission.member_referral_label(project.client_referrer) or "",
                ProjectCommission.member_referral_label(project.contractor_referrer) or "",
            ])).lower(),
        })
    return items


def _level_config_maps(scheme):
    levels = get_commission_levels(scheme)
    if levels:
        return (
            {item.level: item.description or "" for item in levels},
            {item.level: float(item.percentage) for item in levels},
        )
    defaults = (
        DEFAULT_CLIENT_COMMISSION_LEVELS
        if scheme == COMMISSION_SCHEME_CLIENT
        else DEFAULT_CONTRACTOR_COMMISSION_LEVELS
    )
    return (
        {level: desc for level, _pct, desc in defaults},
        {level: float(pct) for level, pct, _desc in defaults},
    )


def _hierarchy_assignment(chain, slot, has_referrer):
    if not has_referrer:
        return "No referrer — share flows to POP"
    if slot == MAX_SHARING_LEVELS:
        return f"Level 7 — credited to {MANDATE_RECIPIENT_LABEL}"
    if slot > len(chain):
        return "No upline at this level — share flows to POP"
    return "Active member in sharing chain"


def _build_hierarchy_details(projects, scheme):
    descriptions, percentages = _level_config_maps(scheme)
    referrer_key = (
        "client_referrer_id"
        if scheme == COMMISSION_SCHEME_CLIENT
        else "contractor_referrer_id"
    )
    scheme_label = "Ref-Client" if scheme == COMMISSION_SCHEME_CLIENT else "Ref-Contractor"

    rows = []
    for project in projects:
        referrer_id = project.get(referrer_key)
        chain = build_sharing_chain(referrer_id) if referrer_id else []

        for slot in range(1, MAX_SHARING_LEVELS + 1):
            if slot == MAX_SHARING_LEVELS:
                member_id = None
                member_name = MANDATE_RECIPIENT_LABEL
                account_type = "Mandate"
            elif not referrer_id:
                member_id = None
                member_name = "—"
                account_type = "—"
            elif slot <= len(chain):
                member = chain[slot - 1]
                member_id = member.member_id
                member_name = member.full_name
                account_type = "Member"
            else:
                member_id = None
                member_name = "—"
                account_type = "—"

            rows.append({
                "project_id": project["project_id"],
                "project_title": project["project_title"],
                "scheme_label": scheme_label,
                "level": slot,
                "level_label": f"L{slot}",
                "percentage": _money(percentages.get(slot, 0)),
                "role_description": descriptions.get(slot, ""),
                "member_id": member_id,
                "member_name": member_name,
                "account_type": account_type,
                "assignment": _hierarchy_assignment(chain, slot, bool(referrer_id)),
                "search_text": " ".join(filter(None, [
                    project["project_title"],
                    str(project["project_id"]),
                    member_name if member_name != "—" else "",
                    descriptions.get(slot, ""),
                    scheme_label,
                ])).lower(),
            })

    return {
        "rows": rows,
        "project_count": len(projects),
        "scheme_label": scheme_label,
    }


def project_detail_report(project_id):
    project = (
        ProjectCommission.query
        .options(
            joinedload(ProjectCommission.contractor),
            joinedload(ProjectCommission.client_referrer),
            joinedload(ProjectCommission.contractor_referrer),
        )
        .filter_by(project_id=project_id)
        .first()
    )
    if not project:
        return None

    entries = (
        SharingEntry.query
        .filter_by(project_id=project_id)
        .join(SharingBatch)
        .options(
            joinedload(SharingEntry.member),
            joinedload(SharingEntry.billing),
            joinedload(SharingEntry.batch),
        )
        .order_by(
            SharingBatch.commission_date.desc(),
            SharingEntry.share_scheme.asc(),
            SharingEntry.level.asc(),
            SharingEntry.entry_id.asc(),
        )
        .all()
    )
    if not entries:
        return None

    grouped = defaultdict(list)
    for entry in entries:
        grouped[(entry.batch_id, entry.billing_id)].append(entry)

    generations = []
    for (batch_id, billing_id), group in sorted(
        grouped.items(),
        key=lambda item: item[1][0].batch.commission_date,
        reverse=True,
    ):
        batch = group[0].batch
        billing = group[0].billing
        rows = [_entry_row(e) for e in group]
        generations.append({
            "batch_id": batch_id,
            "billing_id": billing_id,
            "billing_date": batch.commission_date.isoformat(),
            "generated_at": batch.generated_at.strftime("%Y-%m-%d %H:%M"),
            "billing_amount": _money(billing.billing_amount if billing else 0),
            "entries": rows,
            "total_shared": _money(sum(r["share_amount"] for r in rows)),
            "total_to_members": _money(
                sum(r["share_amount"] for r in rows if r["recipient_type"] == "member")
            ),
            "total_admin": _money(
                sum(r["share_amount"] for r in rows if r["recipient_type"] == "admin")
            ),
            "total_pop": _money(
                sum(r["share_amount"] for r in rows if r["recipient_type"] == "pop")
            ),
        })

    all_entry_rows = [row for generation in generations for row in generation["entries"]]
    recipient_summary = summarize_recipient_totals(all_entry_rows)

    return {
        "project": {
            "project_id": project.project_id,
            "project_title": project.project_title,
            "address": project.address,
            "contractor_name": project.contractor.company_name if project.contractor else "—",
            "client_referrer_label": ProjectCommission.member_referral_label(project.client_referrer),
            "contractor_referrer_label": ProjectCommission.member_referral_label(project.contractor_referrer),
        },
        "generations": generations,
        "recipient_summary": recipient_summary,
        "pool_split": {
            "client_percent": CLIENT_POOL_PERCENT,
            "contractor_percent": CONTRACTOR_POOL_PERCENT,
            "admin_percent": ADMIN_ACCOUNT_PERCENT,
        },
    }


def commission_summary_report():
    projects = generated_projects_index()
    if not projects:
        return _empty_commission_report()

    all_entries = (
        SharingEntry.query
        .join(SharingBatch)
        .options(
            joinedload(SharingEntry.member),
            joinedload(SharingEntry.project),
            joinedload(SharingEntry.batch),
        )
        .order_by(
            SharingEntry.project_id.asc(),
            SharingBatch.commission_date.asc(),
            SharingEntry.share_scheme.asc(),
            SharingEntry.level.asc(),
            SharingEntry.entry_id.asc(),
        )
        .all()
    )
    detail_rows = [_detail_entry_row(entry) for entry in all_entries]

    entry_stats = (
        db.session.query(
            SharingEntry.project_id,
            SharingEntry.recipient_type,
            SharingEntry.share_scheme,
            SharingEntry.recipient_label,
            func.sum(SharingEntry.share_amount),
        )
        .group_by(
            SharingEntry.project_id,
            SharingEntry.recipient_type,
            SharingEntry.share_scheme,
            SharingEntry.recipient_label,
        )
        .all()
    )
    stats_map = _aggregate_stats_map(entry_stats)

    return {
        "project_details": {"rows": projects, "project_count": len(projects)},
        "client_hierarchy": _build_hierarchy_details(projects, COMMISSION_SCHEME_CLIENT),
        "contractor_hierarchy": _build_hierarchy_details(projects, COMMISSION_SCHEME_CONTRACTOR),
        "main_pools": _build_main_pools_table(projects, stats_map),
        "client_details": _build_scheme_detail_table(
            detail_rows,
            "client",
            pool_percent=CLIENT_POOL_PERCENT,
            include_pool_balance=True,
        ),
        "contractor_details": _build_scheme_detail_table(
            detail_rows,
            "contractor",
            pool_percent=CONTRACTOR_POOL_PERCENT,
            include_pool_balance=True,
        ),
        "platform_details": _build_platform_breakdown_table(projects, stats_map),
        "member_summary": _build_member_earnings_summary(detail_rows),
        "mandate_account": _build_mandate_account_summary(detail_rows, projects),
        "pop_and_platform": _build_pop_and_platform_tables(detail_rows, projects),
        "pool_split": {
            "client_percent": CLIENT_POOL_PERCENT,
            "contractor_percent": CONTRACTOR_POOL_PERCENT,
            "admin_percent": ADMIN_ACCOUNT_PERCENT,
        },
        "platform_breakdown": _platform_breakdown_config(),
        "pop_label": POP_RECIPIENT_LABEL,
        "has_data": True,
    }


def _empty_totals():
    return {
        "project_count": 0,
        "total_commission": 0,
        "client_pool": 0,
        "contractor_pool": 0,
        "platform_founders": 0,
        "platform_ref_client": 0,
        "platform_ref_contractor": 0,
        "platform_pop": 0,
        "platform_main": 0,
        "platform_total": 0,
        "member_share": 0,
        "mandate_share": 0,
        "pop_share": 0,
        "total_distributed": 0,
    }


def _platform_breakdown_config():
    return {
        "founders_prerogative": 5,
        "platform_ref_client": 12,
        "platform_ref_contractor": 8,
        "platform_pop": 10,
        "platform_main": 65,
    }


def _quantize_share_amount(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _split_platform_pool(platform_pool):
    """Mirror PLATFORM sub-account split from prof_sharing_service._platform_entries."""
    pool = _quantize_share_amount(platform_pool)
    founders = _quantize_share_amount(pool * Decimal("0.05"))
    plat_client = _quantize_share_amount(pool * Decimal("0.12"))
    plat_contractor = _quantize_share_amount(pool * Decimal("0.08"))
    plat_pop = _quantize_share_amount(pool * Decimal("0.10"))
    plat_main = _quantize_share_amount(pool - founders - plat_client - plat_contractor - plat_pop)
    return {
        "platform_founders": founders,
        "platform_ref_client": plat_client,
        "platform_ref_contractor": plat_contractor,
        "platform_pop": plat_pop,
        "platform_main": plat_main,
    }


def _detail_entry_row(entry):
    member = entry.member
    project = entry.project
    batch = entry.batch
    row = _entry_row(entry)
    row.update({
        "project_id": entry.project_id,
        "project_title": project.project_title if project else "—",
        "billing_date": batch.commission_date.isoformat() if batch and batch.commission_date else "—",
        "search_text": " ".join(filter(None, [
            project.project_title if project else "",
            member.full_name if member else (entry.recipient_label or ""),
            str(entry.member_id or ""),
            row["level_label"],
        ])).lower(),
    })
    return row


def _aggregate_stats_map(entry_stats):
    stats_map = defaultdict(lambda: {
        "client_pool": Decimal("0"),
        "contractor_pool": Decimal("0"),
        "platform": Decimal("0"),
        "platform_founders": Decimal("0"),
        "platform_main": Decimal("0"),
        "platform_ref_client": Decimal("0"),
        "platform_ref_contractor": Decimal("0"),
        "platform_pop": Decimal("0"),
        "members": Decimal("0"),
        "mandate": Decimal("0"),
        "pop": Decimal("0"),
    })

    for project_id, recipient_type, share_scheme, recipient_label, amount in entry_stats:
        value = Decimal(str(amount or 0))
        bucket = stats_map[project_id]
        if recipient_type == "pop":
            bucket["pop"] += value
        elif recipient_type == "admin":
            bucket["platform"] += value
            label = (recipient_label or "").lower()
            if "founders_prerogative" in label:
                bucket["platform_founders"] += value
            else:
                bucket["platform_main"] += value
        elif recipient_type == "mandate":
            bucket["mandate"] += value
        elif recipient_type == "member":
            bucket["members"] += value

        if share_scheme == "client":
            bucket["client_pool"] += value
        elif share_scheme == "contractor":
            bucket["contractor_pool"] += value
        elif share_scheme == "platform_ref_client":
            bucket["platform_ref_client"] += value
        elif share_scheme == "platform_ref_contractor":
            bucket["platform_ref_contractor"] += value
        elif share_scheme == "platform_pop":
            bucket["platform_pop"] += value

    return stats_map


def _build_main_pools_table(projects, stats_map):
    rows = []
    totals = _empty_totals()
    split = {
        "client_percent": CLIENT_POOL_PERCENT,
        "contractor_percent": CONTRACTOR_POOL_PERCENT,
        "platform_percent": ADMIN_ACCOUNT_PERCENT,
    }

    for item in projects:
        commission = Decimal(str(item["total_commission"]))
        client_pool = commission * Decimal(str(CLIENT_POOL_PERCENT)) / Decimal("100")
        contractor_pool = commission * Decimal(str(CONTRACTOR_POOL_PERCENT)) / Decimal("100")
        platform_pool = commission * Decimal(str(ADMIN_ACCOUNT_PERCENT)) / Decimal("100")
        row = {
            **item,
            "client_pool": _money(client_pool),
            "contractor_pool": _money(contractor_pool),
            "platform_pool": _money(platform_pool),
        }
        rows.append(row)
        totals["project_count"] += 1
        totals["total_commission"] += item["total_commission"]
        totals["client_pool"] += row["client_pool"]
        totals["contractor_pool"] += row["contractor_pool"]
        totals["platform_total"] += row["platform_pool"]

    for key in totals:
        if key != "project_count":
            totals[key] = _money(totals[key])

    return {"rows": rows, "totals": totals, "split": split}


def _build_scheme_detail_table(entry_rows, share_scheme, pool_percent=None, include_pool_balance=False):
    groups = defaultdict(lambda: {
        "project_id": None,
        "project_title": "",
        "billing_date": "",
        "members": [],
        "mandate_amount": Decimal("0"),
        "mandate_label": MANDATE_RECIPIENT_LABEL,
        "pop_amount": Decimal("0"),
        "pop_label": POP_RECIPIENT_LABEL,
    })

    for row in entry_rows:
        if row["share_scheme"] != share_scheme:
            continue
        key = (row["project_id"], row["billing_date"])
        group = groups[key]
        group["project_id"] = row["project_id"]
        group["project_title"] = row["project_title"]
        group["billing_date"] = row["billing_date"]
        amount = Decimal(str(row["share_amount"]))
        if row["recipient_type"] == "member":
            group["members"].append(row)
        elif row["recipient_type"] == "mandate" and include_pool_balance:
            group["mandate_amount"] += amount
            group["mandate_label"] = row.get("recipient_label") or row["member_name"] or MANDATE_RECIPIENT_LABEL
        elif row["recipient_type"] == "pop" and include_pool_balance:
            group["pop_amount"] += amount
            group["pop_label"] = row.get("recipient_label") or row["member_name"] or POP_RECIPIENT_LABEL

    combined = []
    member_total = Decimal("0")
    mandate_total = Decimal("0")
    pop_total = Decimal("0")
    member_count = 0

    for key in sorted(groups.keys(), key=lambda item: (groups[item]["billing_date"], groups[item]["project_title"])):
        group = groups[key]
        group["members"].sort(key=lambda item: (
            item["level"] if item["level"] > 0 else 99,
            item["member_name"],
        ))
        for member_row in group["members"]:
            amount = Decimal(str(member_row["share_amount"]))
            member_total += amount
            member_count += 1
            combined.append({**member_row, "is_pop_row": False, "is_mandate_row": False})

        if include_pool_balance and group["mandate_amount"] > 0:
            mandate_total += group["mandate_amount"]
            combined.append({
                "project_id": group["project_id"],
                "project_title": group["project_title"],
                "billing_date": group["billing_date"],
                "member_name": group["mandate_label"],
                "member_id": None,
                "account_type": "Mandate",
                "level_label": "L7",
                "level": MAX_SHARING_LEVELS,
                "percentage": None,
                "share_amount": _money(group["mandate_amount"]),
                "share_scheme": share_scheme,
                "recipient_type": "mandate",
                "is_pop_row": False,
                "is_mandate_row": True,
                "search_text": " ".join(filter(None, [
                    group["project_title"],
                    group["mandate_label"],
                    "mandate",
                ])).lower(),
            })

        if include_pool_balance and group["pop_amount"] > 0:
            pop_total += group["pop_amount"]
            combined.append({
                "project_id": group["project_id"],
                "project_title": group["project_title"],
                "billing_date": group["billing_date"],
                "member_name": group["pop_label"],
                "member_id": None,
                "account_type": "POP",
                "level_label": "POP",
                "level": 0,
                "percentage": None,
                "share_amount": _money(group["pop_amount"]),
                "share_scheme": share_scheme,
                "recipient_type": "pop",
                "is_pop_row": True,
                "is_mandate_row": False,
                "search_text": " ".join(filter(None, [
                    group["project_title"],
                    group["pop_label"],
                    "pop",
                ])).lower(),
            })

    pool_total = member_total + mandate_total + pop_total
    result = {
        "rows": combined,
        "total": _money(pool_total),
        "entry_count": member_count + sum(1 for row in combined if row.get("is_pop_row") or row.get("is_mandate_row")),
        "member_count": member_count,
    }
    if include_pool_balance:
        result.update({
            "member_total": _money(member_total),
            "mandate_total": _money(mandate_total),
            "pop_total": _money(pop_total),
            "pool_percent": pool_percent,
            "pop_row_count": sum(1 for row in combined if row.get("is_pop_row")),
            "mandate_row_count": sum(1 for row in combined if row.get("is_mandate_row")),
        })
    return result


def _build_platform_breakdown_table(projects, stats_map=None):
    rows = []
    totals = {
        "platform_pool": Decimal("0"),
        "platform_founders": Decimal("0"),
        "platform_ref_client": Decimal("0"),
        "platform_ref_contractor": Decimal("0"),
        "platform_pop": Decimal("0"),
        "platform_main": Decimal("0"),
    }

    for item in projects:
        commission = Decimal(str(item["total_commission"]))
        platform_pool = commission * Decimal(str(ADMIN_ACCOUNT_PERCENT)) / Decimal("100")
        split = _split_platform_pool(platform_pool)
        row = {
            "project_id": item["project_id"],
            "project_title": item["project_title"],
            "contractor_name": item["contractor_name"],
            "total_commission": item["total_commission"],
            "platform_pool": _money(platform_pool),
            "platform_founders": _money(split["platform_founders"]),
            "platform_ref_client": _money(split["platform_ref_client"]),
            "platform_ref_contractor": _money(split["platform_ref_contractor"]),
            "platform_pop": _money(split["platform_pop"]),
            "platform_main": _money(split["platform_main"]),
            "search_text": item.get("search_text", ""),
        }
        rows.append(row)
        totals["platform_pool"] += platform_pool
        totals["platform_founders"] += split["platform_founders"]
        totals["platform_ref_client"] += split["platform_ref_client"]
        totals["platform_ref_contractor"] += split["platform_ref_contractor"]
        totals["platform_pop"] += split["platform_pop"]
        totals["platform_main"] += split["platform_main"]

    return {
        "rows": rows,
        "totals": {key: _money(value) for key, value in totals.items()},
        "breakdown": _platform_breakdown_config(),
    }


POP_SOURCE_LABELS = {
    "ref_client": "Ref-Client pool — unfilled upline / overflow to POP",
    "ref_contractor": "Ref-Contractor pool — unfilled upline / overflow to POP",
    "platform_pop": "Platform POP — 10% direct allocation from PLATFORM pool",
    "platform_ref_client": "Platform Ref-Client pool — unfilled upline / overflow to POP",
    "platform_ref_contractor": "Platform Ref-Contractor pool — unfilled upline / overflow to POP",
    "cap_flush": "Earnings cap overflow — excess redirected to POP",
    "other": "Other POP entries",
}


def _pop_source_key_row(row):
    label = row.get("recipient_label") or ""
    if POP_CAP_FLUSH_LABEL in label or "earnings cap" in label.lower():
        return "cap_flush"
    scheme = row.get("share_scheme") or ""
    if scheme == "client":
        return "ref_client"
    if scheme == "contractor":
        return "ref_contractor"
    if scheme == "platform_pop":
        return "platform_pop"
    if scheme == "platform_ref_client":
        return "platform_ref_client"
    if scheme == "platform_ref_contractor":
        return "platform_ref_contractor"
    return "other"


def _build_earnings_summary(entry_rows, recipient_types=("member",)):
    buckets = defaultdict(lambda: {
        "member_id": None,
        "member_name": "",
        "transaction_count": 0,
        "ref_client": Decimal("0"),
        "ref_contractor": Decimal("0"),
        "platform_ref_client": Decimal("0"),
        "platform_ref_contractor": Decimal("0"),
        "total": Decimal("0"),
        "search_text": "",
    })

    for row in entry_rows:
        if row["recipient_type"] not in recipient_types:
            continue
        scheme = row.get("share_scheme")
        if scheme not in ("client", "contractor", "platform_ref_client", "platform_ref_contractor"):
            continue

        member_id = row.get("member_id") or 0
        name = row.get("member_name") or "—"
        key = (member_id, name)
        bucket = buckets[key]
        bucket["member_id"] = member_id if member_id else None
        bucket["member_name"] = name
        bucket["transaction_count"] += 1
        amount = Decimal(str(row.get("share_amount") or 0))
        bucket["total"] += amount
        if scheme == "client":
            bucket["ref_client"] += amount
        elif scheme == "contractor":
            bucket["ref_contractor"] += amount
        elif scheme == "platform_ref_client":
            bucket["platform_ref_client"] += amount
        elif scheme == "platform_ref_contractor":
            bucket["platform_ref_contractor"] += amount

    summary_rows = []
    column_totals = {
        "ref_client": Decimal("0"),
        "ref_contractor": Decimal("0"),
        "platform_ref_client": Decimal("0"),
        "platform_ref_contractor": Decimal("0"),
        "total": Decimal("0"),
    }
    for bucket in buckets.values():
        for col in column_totals:
            column_totals[col] += bucket[col]
        bucket["ref_client"] = _money(bucket["ref_client"])
        bucket["ref_contractor"] = _money(bucket["ref_contractor"])
        bucket["platform_ref_client"] = _money(bucket["platform_ref_client"])
        bucket["platform_ref_contractor"] = _money(bucket["platform_ref_contractor"])
        bucket["total"] = _money(bucket["total"])
        bucket["search_text"] = " ".join([
            bucket["member_name"],
            str(bucket["member_id"] or ""),
        ]).lower()
        summary_rows.append(bucket)

    summary_rows.sort(key=lambda item: (-item["total"], item["member_name"]))
    return {
        "rows": summary_rows,
        "member_count": len(summary_rows),
        "column_totals": {key: _money(value) for key, value in column_totals.items()},
    }


def _build_member_earnings_summary(entry_rows):
    return _build_earnings_summary(entry_rows, recipient_types=("member",))


def _build_mandate_account_summary(entry_rows, projects):
    by_source = defaultdict(lambda: {"amount": Decimal("0"), "entry_count": 0})
    by_project = defaultdict(lambda: defaultdict(Decimal))
    project_titles = {item["project_id"]: item["project_title"] for item in projects}

    for row in entry_rows:
        if row["recipient_type"] != "mandate":
            continue
        scheme = row.get("share_scheme") or "other"
        if scheme not in MANDATE_SUBACCOUNT_LABELS:
            continue
        amount = Decimal(str(row.get("share_amount") or 0))
        pid = row["project_id"]
        by_source[scheme]["amount"] += amount
        by_source[scheme]["entry_count"] += 1
        by_project[pid][scheme] += amount

    source_rows = []
    source_total = Decimal("0")
    for scheme_key in (
        "client",
        "contractor",
        "platform_ref_client",
        "platform_ref_contractor",
    ):
        bucket = by_source.get(scheme_key)
        if not bucket or bucket["amount"] <= 0:
            continue
        source_rows.append({
            "scheme_key": scheme_key,
            "source_label": MANDATE_SUBACCOUNT_LABELS[scheme_key],
            "entry_count": bucket["entry_count"],
            "amount": _money(bucket["amount"]),
        })
        source_total += bucket["amount"]

    project_rows = []
    project_total = Decimal("0")
    project_ids = {item["project_id"] for item in projects}
    project_ids.update(by_project.keys())
    for pid in sorted(project_ids, key=lambda value: project_titles.get(value, "")):
        sources = by_project.get(pid, {})
        row_total = sum(sources.values())
        project_rows.append({
            "project_id": pid,
            "project_title": project_titles.get(pid, f"Project #{pid}"),
            "ref_client": _money(sources.get("client", 0)),
            "ref_contractor": _money(sources.get("contractor", 0)),
            "platform_ref_client": _money(sources.get("platform_ref_client", 0)),
            "platform_ref_contractor": _money(sources.get("platform_ref_contractor", 0)),
            "total": _money(row_total),
        })
        project_total += row_total

    return {
        "by_source": source_rows,
        "by_project": project_rows,
        "source_total": _money(source_total),
        "project_total": _money(project_total),
        "mandate_label": MANDATE_RECIPIENT_LABEL,
    }


def _build_pop_and_platform_tables(entry_rows, projects):
    pop_by_source = defaultdict(lambda: {"amount": Decimal("0"), "entry_count": 0})
    pop_by_project = defaultdict(lambda: defaultdict(Decimal))

    project_titles = {item["project_id"]: item["project_title"] for item in projects}

    for row in entry_rows:
        if row["recipient_type"] != "pop":
            continue
        amount = Decimal(str(row.get("share_amount") or 0))
        pid = row["project_id"]
        source = _pop_source_key_row(row)
        pop_by_source[source]["amount"] += amount
        pop_by_source[source]["entry_count"] += 1
        pop_by_project[pid][source] += amount

    pop_source_rows = []
    pop_source_total = Decimal("0")
    for source_key in (
        "ref_client",
        "ref_contractor",
        "platform_pop",
        "platform_ref_client",
        "platform_ref_contractor",
        "cap_flush",
        "other",
    ):
        bucket = pop_by_source.get(source_key)
        if not bucket or bucket["amount"] <= 0:
            continue
        pop_source_rows.append({
            "source_key": source_key,
            "source_label": POP_SOURCE_LABELS[source_key],
            "entry_count": bucket["entry_count"],
            "amount": _money(bucket["amount"]),
        })
        pop_source_total += bucket["amount"]

    pop_project_rows = []
    pop_project_total = Decimal("0")
    project_ids = {item["project_id"] for item in projects}
    project_ids.update(pop_by_project.keys())
    for pid in sorted(project_ids, key=lambda value: project_titles.get(value, "")):
        sources = pop_by_project.get(pid, {})
        row_total = sum(sources.values())
        pop_project_rows.append({
            "project_id": pid,
            "project_title": project_titles.get(pid, f"Project #{pid}"),
            "ref_client": _money(sources.get("ref_client", 0)),
            "ref_contractor": _money(sources.get("ref_contractor", 0)),
            "platform_pop": _money(sources.get("platform_pop", 0)),
            "platform_ref_client": _money(sources.get("platform_ref_client", 0)),
            "platform_ref_contractor": _money(sources.get("platform_ref_contractor", 0)),
            "cap_flush": _money(sources.get("cap_flush", 0)),
            "other": _money(sources.get("other", 0)),
            "total": _money(row_total),
        })
        pop_project_total += row_total

    platform_rows = []
    platform_totals = {"founders": Decimal("0"), "platform_main": Decimal("0")}
    for item in sorted(projects, key=lambda row: row["project_title"]):
        pid = item["project_id"]
        commission = Decimal(str(item["total_commission"]))
        platform_pool = commission * Decimal(str(ADMIN_ACCOUNT_PERCENT)) / Decimal("100")
        split = _split_platform_pool(platform_pool)
        founders = split["platform_founders"]
        platform_main = split["platform_main"]
        row_total = founders + platform_main
        platform_rows.append({
            "project_id": pid,
            "project_title": project_titles.get(pid, f"Project #{pid}"),
            "founders": _money(founders),
            "platform_main": _money(platform_main),
            "total": _money(row_total),
        })
        platform_totals["founders"] += founders
        platform_totals["platform_main"] += platform_main

    platform_grand = platform_totals["founders"] + platform_totals["platform_main"]
    return {
        "pop_summary": {
            "by_source": pop_source_rows,
            "by_project": pop_project_rows,
            "source_total": _money(pop_source_total),
            "project_total": _money(pop_project_total),
            "pop_label": POP_RECIPIENT_LABEL,
        },
        "platform": {
            "by_project": platform_rows,
            "founders_total": _money(platform_totals["founders"]),
            "platform_main_total": _money(platform_totals["platform_main"]),
            "grand_total": _money(platform_grand),
            "founders_label": f"{ADMIN_RECIPIENT_LABEL} — founders_prerogative (5% of PLATFORM pool)",
            "platform_main_label": f"{ADMIN_RECIPIENT_LABEL} — platform (65% of PLATFORM pool)",
        },
    }


def _empty_commission_report():
    return {
        "project_details": {"rows": [], "project_count": 0},
        "client_hierarchy": _build_hierarchy_details([], COMMISSION_SCHEME_CLIENT),
        "contractor_hierarchy": _build_hierarchy_details([], COMMISSION_SCHEME_CONTRACTOR),
        "main_pools": _build_main_pools_table([], {}),
        "client_details": _build_scheme_detail_table(
            [],
            "client",
            pool_percent=CLIENT_POOL_PERCENT,
            include_pool_balance=True,
        ),
        "contractor_details": _build_scheme_detail_table(
            [],
            "contractor",
            pool_percent=CONTRACTOR_POOL_PERCENT,
            include_pool_balance=True,
        ),
        "platform_details": _build_platform_breakdown_table([], {}),
        "member_summary": _build_member_earnings_summary([]),
        "mandate_account": _build_mandate_account_summary([], []),
        "pop_and_platform": _build_pop_and_platform_tables([], []),
        "pool_split": {
            "client_percent": CLIENT_POOL_PERCENT,
            "contractor_percent": CONTRACTOR_POOL_PERCENT,
            "admin_percent": ADMIN_ACCOUNT_PERCENT,
        },
        "platform_breakdown": _platform_breakdown_config(),
        "pop_label": POP_RECIPIENT_LABEL,
        "has_data": False,
    }
