from pathlib import Path

from app import db
from app.config import MEMBERS_XLSX, SUPPLIERS_SHEET
from app.import_service import _clean_str, _parse_date, _read_excel
from app.models import Member, Supplier

REQUIRED_COLUMNS = {
    "supplier_id",
    "batch",
    "member_referrer_id",
    "company_name",
    "company_address",
    "representative_name",
    "contact_no",
    "date_joined",
}


def load_suppliers_dataframe(source):
    try:
        df = _read_excel(source, sheet_name=SUPPLIERS_SHEET)
    except ValueError as exc:
        raise ValueError(
            f'Excel file must contain a "{SUPPLIERS_SHEET}" sheet with supplier data.'
        ) from exc

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in suppliers sheet: {', '.join(sorted(missing))}")

    if df.empty:
        raise ValueError("The suppliers sheet has no data rows.")

    return df


def _row_payload(row):
    supplier_id = int(row["supplier_id"])
    member_referrer_id = int(row["member_referrer_id"])

    return supplier_id, {
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


def preview_suppliers_dataframe(df, limit=5):
    rows = sorted(df.to_dict("records"), key=lambda r: (int(r["batch"]), int(r["supplier_id"])))
    preview = []
    for row in rows[:limit]:
        supplier_id, payload = _row_payload(row)
        preview.append({
            "supplier_id": supplier_id,
            "company_name": payload["company_name"],
            "batch": payload["batch"],
            "member_referrer_id": payload["member_referrer_id"],
            "representative_name": payload["representative_name"],
            "date_joined": payload["date_joined"].isoformat() if payload["date_joined"] else None,
        })
    return {"row_count": len(rows), "preview": preview}


def import_suppliers_dataframe(df, replace=False):
    if replace:
        Supplier.query.delete()
        db.session.commit()

    imported = 0
    updated = 0
    rows = sorted(df.to_dict("records"), key=lambda r: (int(r["batch"]), int(r["supplier_id"])))

    for row in rows:
        supplier_id, payload = _row_payload(row)
        if not payload["company_name"]:
            raise ValueError(f"Row with supplier_id {supplier_id} is missing company_name.")

        _validate_member_referrer(payload["member_referrer_id"])

        supplier = db.session.get(Supplier, supplier_id)
        if supplier:
            for key, value in payload.items():
                setattr(supplier, key, value)
            updated += 1
        else:
            db.session.add(Supplier(supplier_id=supplier_id, **payload))
            imported += 1

    db.session.commit()
    return {"imported": imported, "updated": updated, "total": Supplier.query.count()}


def import_suppliers_from_upload(file_storage, replace=False):
    df = load_suppliers_dataframe(file_storage)
    return import_suppliers_dataframe(df, replace=replace)


def preview_suppliers_upload(file_storage, limit=5):
    df = load_suppliers_dataframe(file_storage)
    return preview_suppliers_dataframe(df, limit=limit)


def import_suppliers_from_xlsx(path=None, replace=False):
    xlsx_path = Path(path or MEMBERS_XLSX)
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Members file not found: {xlsx_path}")

    df = load_suppliers_dataframe(xlsx_path)
    return import_suppliers_dataframe(df, replace=replace)
