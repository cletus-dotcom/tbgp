from pathlib import Path

import pandas as pd

from app import db
from app.config import CONTRACTORS_SHEET, MEMBERS_XLSX
from app.import_service import _clean_str, _parse_date, _read_excel
from app.models import Contractor, Member

REQUIRED_COLUMNS = {
    "contractor_id",
    "batch",
    "member_referrer_id",
    "company_name",
    "company_address",
    "representative_name",
    "contact_no",
    "date_joined",
}


def load_contractors_dataframe(source):
    try:
        df = _read_excel(source, sheet_name=CONTRACTORS_SHEET)
    except ValueError as exc:
        raise ValueError(
            f'Excel file must contain a "{CONTRACTORS_SHEET}" sheet with contractor data.'
        ) from exc

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in contractors sheet: {', '.join(sorted(missing))}")

    if df.empty:
        raise ValueError("The contractors sheet has no data rows.")

    return df


def _row_payload(row):
    contractor_id = int(row["contractor_id"])
    member_referrer_id = int(row["member_referrer_id"])

    return contractor_id, {
        "batch": int(row["batch"]),
        "member_referrer_id": member_referrer_id,
        "company_name": _clean_str(row["company_name"]) or "",
        "company_address": _clean_str(row["company_address"]),
        "representative_name": _clean_str(row["representative_name"]),
        "contact_no": _clean_str(row["contact_no"]),
        "date_joined": _parse_date(row["date_joined"]),
    }


def _validate_member_referrer(member_referrer_id):
    if not db.session.get(Member, member_referrer_id):
        raise ValueError(f"Member referrer #{member_referrer_id} not found in members table.")


def preview_contractors_dataframe(df, limit=5):
    rows = sorted(df.to_dict("records"), key=lambda r: (int(r["batch"]), int(r["contractor_id"])))
    preview = []
    for row in rows[:limit]:
        contractor_id, payload = _row_payload(row)
        preview.append({
            "contractor_id": contractor_id,
            "company_name": payload["company_name"],
            "batch": payload["batch"],
            "member_referrer_id": payload["member_referrer_id"],
            "representative_name": payload["representative_name"],
            "date_joined": payload["date_joined"].isoformat() if payload["date_joined"] else None,
        })
    return {"row_count": len(rows), "preview": preview}


def import_contractors_dataframe(df, replace=False):
    if replace:
        Contractor.query.delete()
        db.session.commit()

    imported = 0
    updated = 0
    rows = sorted(df.to_dict("records"), key=lambda r: (int(r["batch"]), int(r["contractor_id"])))

    for row in rows:
        contractor_id, payload = _row_payload(row)
        if not payload["company_name"]:
            raise ValueError(f"Row with contractor_id {contractor_id} is missing company_name.")

        _validate_member_referrer(payload["member_referrer_id"])

        contractor = db.session.get(Contractor, contractor_id)
        if contractor:
            for key, value in payload.items():
                setattr(contractor, key, value)
            updated += 1
        else:
            db.session.add(Contractor(contractor_id=contractor_id, **payload))
            imported += 1

    db.session.commit()
    return {"imported": imported, "updated": updated, "total": Contractor.query.count()}


def import_contractors_from_upload(file_storage, replace=False):
    df = load_contractors_dataframe(file_storage)
    return import_contractors_dataframe(df, replace=replace)


def preview_contractors_upload(file_storage, limit=5):
    df = load_contractors_dataframe(file_storage)
    return preview_contractors_dataframe(df, limit=limit)


def import_contractors_from_xlsx(path=None, replace=False):
    xlsx_path = Path(path or MEMBERS_XLSX)
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Members file not found: {xlsx_path}")

    df = load_contractors_dataframe(xlsx_path)
    return import_contractors_dataframe(df, replace=replace)
