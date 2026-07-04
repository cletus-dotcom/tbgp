from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd

from app import db
from app.config import (
    MEMBER_LIFETIME_EARNINGS_CAP,
    MEMBER_SEPARATION_TYPES,
    MEMBER_STATUSES,
    MEMBERS_SHEET,
    MEMBERS_XLSX,
    is_admin_role,
)
from app.models import Member

REQUIRED_COLUMNS = {
    "member_id",
    "batch",
    "referrer_id",
    "date_joined",
    "last_name",
    "first_name",
    "middle_name",
    "suffix",
    "address",
    "phone",
    "email",
    "birth_date",
    "gender",
    "civil_status",
    "highest_education",
    "occupation_income_source",
    "monthly_income",
    "number_of_dependents",
    "beneficiary_name",
    "beneficiary_address",
    "beneficiary_phone",
    "status",
    "termination_date",
    "termination_type",
}


def _parse_date(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.date()
    if hasattr(value, "date") and not isinstance(value, str):
        try:
            return value.date()
        except (AttributeError, TypeError, ValueError):
            pass

    text = str(value).strip()
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _clean_str(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _parse_int(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    return int(float(text))


def _parse_bool(value, default=True):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    text = str(value).strip().lower()
    if not text:
        return default
    return text in ("1", "true", "yes", "y", "on")


def _parse_decimal(value, default):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    text = str(value).strip().replace(",", "")
    if not text:
        return default
    return float(text)


def _read_excel(source, sheet_name=None):
    if isinstance(source, (str, Path)):
        return pd.read_excel(source, sheet_name=sheet_name) if sheet_name else pd.read_excel(source)
    if hasattr(source, "read"):
        content = source.read()
        if hasattr(source, "seek"):
            source.seek(0)
        source = BytesIO(content)
    return pd.read_excel(source, sheet_name=sheet_name) if sheet_name else pd.read_excel(source)


def load_members_dataframe(source):
    try:
        df = _read_excel(source, sheet_name=MEMBERS_SHEET)
    except ValueError:
        df = _read_excel(source)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in spreadsheet: {', '.join(sorted(missing))}")

    if df.empty:
        raise ValueError("The spreadsheet has no data rows.")

    return df


def _validate_choice(value, allowed, field_name):
    if value is None:
        return None
    if value not in allowed:
        raise ValueError(f"Invalid {field_name} '{value}'. Allowed: {', '.join(allowed)}.")
    return value


def _row_payload(row, include_lifetime_cap=False):
    member_id = int(row["member_id"])
    referrer_id = None
    if not pd.isna(row["referrer_id"]):
        referrer_id = int(row["referrer_id"])

    status = _validate_choice(
        _clean_str(row["status"]) or "Active",
        MEMBER_STATUSES,
        "status",
    )
    separation_type = _validate_choice(
        _clean_str(row["termination_type"]),
        MEMBER_SEPARATION_TYPES,
        "termination_type",
    )

    payload = {
        "batch": int(row["batch"]),
        "referrer_id": referrer_id,
        "membership_type": _clean_str(row.get("membership_type")),
        "date_joined": _parse_date(row["date_joined"]),
        "last_name": _clean_str(row["last_name"]) or "",
        "first_name": _clean_str(row["first_name"]) or "",
        "middle_name": _clean_str(row["middle_name"]),
        "suffix": _clean_str(row["suffix"]),
        "address": _clean_str(row["address"]),
        "phone": _clean_str(row["phone"]),
        "email": _clean_str(row["email"]),
        "birth_date": _parse_date(row["birth_date"]),
        "gender": _clean_str(row["gender"]),
        "civil_status": _clean_str(row["civil_status"]),
        "highest_education": _clean_str(row["highest_education"]),
        "occupation_income_source": _clean_str(row["occupation_income_source"]),
        "monthly_income": _clean_str(row["monthly_income"]),
        "number_of_dependents": _parse_int(row["number_of_dependents"]),
        "beneficiary_name": _clean_str(row["beneficiary_name"]),
        "beneficiary_address": _clean_str(row["beneficiary_address"]),
        "beneficiary_phone": _clean_str(row["beneficiary_phone"]),
        "status": status,
        "termination_date": _parse_date(row["termination_date"]),
        "termination_type": separation_type,
    }
    if include_lifetime_cap:
        payload.update({
            "lifetime_cap_enabled": _parse_bool(row.get("lifetime_cap_enabled"), True),
            "lifetime_cap_amount": _parse_decimal(
                row.get("lifetime_cap_amount"),
                float(MEMBER_LIFETIME_EARNINGS_CAP),
            ),
        })
    return member_id, payload


def preview_members_dataframe(df, limit=5):
    rows = sorted(df.to_dict("records"), key=lambda r: (int(r["batch"]), int(r["member_id"])))
    preview = []
    for row in rows[:limit]:
        member_id, payload = _row_payload(row)
        preview.append({
            "member_id": member_id,
            "batch": payload["batch"],
            "referrer_id": payload["referrer_id"],
            "status": payload["status"],
            "date_joined": payload["date_joined"].isoformat() if payload["date_joined"] else None,
            "full_name": " ".join(
                p for p in [
                    payload["first_name"],
                    payload["middle_name"],
                    payload["last_name"],
                    payload.get("suffix"),
                ] if p
            ),
        })
    return {"row_count": len(rows), "preview": preview}


def import_members_dataframe(df, replace=False, actor_role=None):
    if replace:
        Member.query.delete()
        db.session.commit()

    imported = 0
    updated = 0
    rows = sorted(df.to_dict("records"), key=lambda r: (int(r["batch"]), int(r["member_id"])))
    include_lifetime_cap = is_admin_role(actor_role)

    for row in rows:
        member_id, payload = _row_payload(row, include_lifetime_cap=include_lifetime_cap)
        if not payload["last_name"] or not payload["first_name"]:
            raise ValueError(f"Row with member_id {member_id} is missing first or last name.")

        member = db.session.get(Member, member_id)
        if member:
            for key, value in payload.items():
                setattr(member, key, value)
            updated += 1
        else:
            db.session.add(Member(member_id=member_id, **payload))
            imported += 1

    db.session.commit()
    return {"imported": imported, "updated": updated, "total": Member.query.count()}


def import_members_from_upload(file_storage, replace=False, actor_role=None):
    df = load_members_dataframe(file_storage)
    return import_members_dataframe(df, replace=replace, actor_role=actor_role)


def preview_members_upload(file_storage, limit=5):
    df = load_members_dataframe(file_storage)
    return preview_members_dataframe(df, limit=limit)


def import_members_from_xlsx(path=None, replace=False, actor_role=None):
    xlsx_path = Path(path or MEMBERS_XLSX)
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Members file not found: {xlsx_path}")

    df = load_members_dataframe(xlsx_path)
    return import_members_dataframe(df, replace=replace, actor_role=actor_role)
