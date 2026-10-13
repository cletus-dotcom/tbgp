import re
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from math import isnan
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.config import (
    MEMBER_SEPARATION_TYPES,
    MEMBER_STATUSES,
    MEMBERS_SHEET,
    MEMBERS_XLSX,
    is_admin_role,
)
from app.models import Member

REQUIRED_COLUMNS = (
    "member_id",
    "batch",
    "referrer_id",
    "last_name",
    "first_name",
    "middle_name",
)

TEXT_COLUMNS = (
    "membership_type",
    "suffix",
    "address",
    "phone",
    "email",
    "gender",
    "civil_status",
    "highest_education",
    "occupation_income_source",
    "monthly_income",
    "beneficiary_name",
    "beneficiary_address",
    "beneficiary_phone",
    "beneficiary_relationship",
    "gcash_number",
    "bank_account_number",
    "bank_name",
    "id_picture_location",
)

DATE_COLUMNS = ("date_joined", "birth_date", "termination_date")

MAX_REPORTED_ISSUES = 25

PLACEHOLDER_VALUES = {"none", "n/a", "na", "-", "--"}


class MemberImportError(ValueError):
    """Validation failed; nothing was written. Carries every row problem found."""

    def __init__(self, errors, warnings=None):
        self.errors = list(errors)
        self.warnings = list(warnings or [])
        count = len(self.errors)
        shown = self.errors[:MAX_REPORTED_ISSUES]
        lines = [f"{count} problem{'s' if count != 1 else ''} found; nothing was imported."]
        lines += [f"- {msg}" for msg in shown]
        if count > len(shown):
            lines.append(f"- ...and {count - len(shown)} more.")
        super().__init__("\n".join(lines))


class SheetRows:
    """Lightweight tabular sheet data without building a pandas DataFrame."""

    def __init__(self, rows, row_numbers=None):
        self._rows = rows
        self.row_numbers = row_numbers or [index + 2 for index in range(len(rows))]

    @property
    def columns(self):
        if not self._rows:
            return []
        return list(self._rows[0].keys())

    @property
    def empty(self):
        return not self._rows

    def to_dict(self, orient="records"):
        if orient != "records":
            raise ValueError("Only orient='records' is supported.")
        return list(self._rows)


def _is_blank(value):
    if value is None:
        return True
    if isinstance(value, float) and isnan(value):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _parse_date(value):
    if _is_blank(value):
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

    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d-%b-%Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _clean_str(value):
    if _is_blank(value):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    return text or None


def _parse_int(value):
    if _is_blank(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _parse_dependents(value):
    parsed = _parse_int(value)
    if parsed is None:
        return None
    if parsed < 0 or parsed > 50:
        return None
    return parsed


def _parse_age(value):
    if _is_blank(value):
        return None
    parsed = _parse_int(value)
    if parsed is not None:
        return parsed if 0 <= parsed <= 130 else None
    text = str(value).strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    try:
        age = int(digits)
    except ValueError:
        return None
    return age if 0 <= age <= 130 else None


def _parse_bool(value, default=True):
    if _is_blank(value):
        return default
    text = str(value).strip().lower()
    if not text:
        return default
    return text in ("1", "true", "yes", "y", "on")


def _parse_decimal(value, default):
    if _is_blank(value):
        return default
    text = str(value).strip().replace(",", "")
    if not text:
        return default
    return float(text)


def _read_excel_openpyxl(source, sheet_name=None):
    import openpyxl

    if isinstance(source, (str, Path)):
        workbook = openpyxl.load_workbook(source, read_only=True, data_only=True)
    else:
        content = source.read()
        if hasattr(source, "seek"):
            source.seek(0)
        workbook = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)

    if sheet_name and sheet_name not in workbook.sheetnames:
        workbook.close()
        raise ValueError(f'Sheet "{sheet_name}" was not found.')

    target_sheet = sheet_name if sheet_name in workbook.sheetnames else workbook.sheetnames[0]
    worksheet = workbook[target_sheet]
    rows = list(worksheet.iter_rows(values_only=True))
    workbook.close()
    if not rows:
        return SheetRows([])

    headers = [str(col).strip() if col is not None else "" for col in rows[0]]
    records = []
    row_numbers = []
    for excel_row, row in enumerate(rows[1:], start=2):
        if row is None or all(_is_blank(cell) for cell in row):
            continue
        record = {}
        for index, header in enumerate(headers):
            if not header:
                continue
            record[header] = row[index] if index < len(row) else None
        if _is_blank(record.get("member_id")) and _is_blank(record.get("contractor_id")) and _is_blank(record.get("supplier_id")):
            first_value = next((record[key] for key in record if not _is_blank(record.get(key))), None)
            if first_value is None:
                continue
        records.append(record)
        row_numbers.append(excel_row)
    return SheetRows(records, row_numbers)


def _read_excel(source, sheet_name=None):
    """Read spreadsheet rows via openpyxl (avoids pandas Excel engine crashes)."""
    return _read_excel_openpyxl(source, sheet_name=sheet_name)


HEADER_ALIASES = {
    "surname": "last_name",
    "given_name": "first_name",
    "referrer": "referrer_id",
    "referred_by": "referrer_id",
}


def _normalize_header(name):
    column = re.sub(r"[^a-z0-9]+", "_", str(name or "").strip().lower()).strip("_")
    return HEADER_ALIASES.get(column, column)


def load_members_dataframe(source):
    try:
        sheet = _read_excel(source, sheet_name=MEMBERS_SHEET)
    except ValueError:
        sheet = _read_excel(source)

    if sheet.empty:
        raise ValueError("The spreadsheet has no data rows.")

    records = []
    for record in sheet.to_dict("records"):
        normalized = {}
        for header, value in record.items():
            column = _normalize_header(header)
            if column and column not in normalized:
                normalized[column] = value
        records.append(normalized)
    sheet = SheetRows(records, sheet.row_numbers)

    missing = [column for column in REQUIRED_COLUMNS if column not in sheet.columns]
    if missing:
        raise ValueError(
            f"Missing columns in spreadsheet: {', '.join(missing)}. "
            f"Required columns: {', '.join(REQUIRED_COLUMNS)}."
        )

    return sheet


def clear_members_and_dependents(*, commit=True):
    """Remove member rows and dependent records that block member deletes/replace imports.

    Preserves user accounts but unlinks them from members. Caller may set commit=False
    to continue the same transaction (e.g. sequence resets after purge).
    """
    from app.models import (
        AdSplitMember,
        Contractor,
        MarketplaceLead,
        MemberLedger,
        MemberPosition,
        MemberSanction,
        OmpdFundEntry,
        PayoutNotification,
        PayoutRequest,
        ProductCommission,
        ProductCommissionAdAllocation,
        ProductCommissionShare,
        ProjectBilling,
        ProjectCommission,
        SharingBatch,
        SharingEntry,
        Supplier,
        User,
    )

    User.query.filter(User.member_id.isnot(None)).update(
        {User.member_id: None},
        synchronize_session=False,
    )
    Member.query.update({Member.referrer_id: None}, synchronize_session=False)
    MarketplaceLead.query.filter(MarketplaceLead.attributed_member_id.isnot(None)).update(
        {MarketplaceLead.attributed_member_id: None},
        synchronize_session=False,
    )

    ProductCommissionAdAllocation.query.delete(synchronize_session=False)
    ProductCommissionShare.query.delete(synchronize_session=False)
    ProductCommission.query.delete(synchronize_session=False)
    AdSplitMember.query.delete(synchronize_session=False)
    MemberPosition.query.delete(synchronize_session=False)
    MemberSanction.query.delete(synchronize_session=False)
    MemberLedger.query.delete(synchronize_session=False)
    PayoutNotification.query.delete(synchronize_session=False)
    OmpdFundEntry.query.delete(synchronize_session=False)
    PayoutRequest.query.delete(synchronize_session=False)
    SharingEntry.query.delete(synchronize_session=False)
    SharingBatch.query.delete(synchronize_session=False)
    ProjectBilling.query.delete(synchronize_session=False)
    ProjectCommission.query.delete(synchronize_session=False)
    Contractor.query.delete(synchronize_session=False)
    Supplier.query.delete(synchronize_session=False)
    Member.query.delete(synchronize_session=False)
    if commit:
        db.session.commit()


def _parse_whole_number(value):
    """Integer from a cell (2003, 2003.0, "2,003"); None when blank. Raises ValueError otherwise."""
    if _is_blank(value):
        return None
    if isinstance(value, bool):
        raise ValueError(value)
    if isinstance(value, int):
        return value
    number = float(str(value).strip().replace(",", ""))
    if not number.is_integer():
        raise ValueError(value)
    return int(number)


def _column_limit(field):
    column = Member.__table__.columns.get(field)
    return getattr(column.type, "length", None) if column is not None else None


def _match_choice(text, allowed):
    return {item.lower(): item for item in allowed}.get(text.lower())


def _is_placeholder(value):
    return _is_blank(value) or str(value).strip().lower() in PLACEHOLDER_VALUES


def _parse_member_row(row, line, include_lifetime_cap, errors, warnings, strict=True):
    """Validate one sheet row. Returns {member_id, referrer_id, values} or None if unusable.

    ``values`` only holds non-blank cells, so blank cells never erase data on existing members.
    """
    where = f"Row {line}"

    def whole_number(field, required, minimum=1):
        raw = row.get(field)
        try:
            value = _parse_whole_number(raw)
        except (TypeError, ValueError):
            errors.append(f"{where}: {field} '{_clean_str(raw)}' is not a whole number.")
            return None
        if value is None:
            if required:
                errors.append(f"{where}: {field} is required.")
            return None
        if value < minimum:
            errors.append(f"{where}: {field} must be {minimum} or more.")
            return None
        return value

    member_id = whole_number("member_id", True)
    if member_id is not None:
        where = f"Row {line} (member {member_id})"
    batch = whole_number("batch", True, minimum=0)
    referrer_id = whole_number("referrer_id", False)
    if referrer_id is not None and referrer_id == member_id:
        errors.append(f"{where}: a member cannot be their own referrer.")
        referrer_id = None

    values = {}
    if batch is not None:
        values["batch"] = batch

    if _clean_str(row.get("last_name")) is None:
        errors.append(f"{where}: last_name is required.")
    if _clean_str(row.get("first_name")) is None:
        if strict:
            errors.append(f"{where}: first_name is required.")
        elif _clean_str(row.get("last_name")):
            row = {**row, "first_name": row.get("last_name")}
            warnings.append(f"{where}: first_name is blank; last_name was used.")

    for field in ("last_name", "first_name", "middle_name") + TEXT_COLUMNS:
        text = _clean_str(row.get(field))
        if text is None:
            continue
        limit = _column_limit(field)
        if limit and len(text) > limit:
            errors.append(f"{where}: {field} has {len(text)} characters; the limit is {limit}.")
            continue
        values[field] = text

    for field in DATE_COLUMNS:
        raw = row.get(field)
        if _is_placeholder(raw):
            continue
        parsed = _parse_date(raw)
        if parsed is None:
            warnings.append(f"{where}: {field} '{_clean_str(raw)}' is not a date (use YYYY-MM-DD); left blank.")
        else:
            values[field] = parsed

    for field, parser in (("number_of_dependents", _parse_dependents), ("age", _parse_age)):
        raw = row.get(field)
        if _is_placeholder(raw):
            continue
        parsed = parser(raw)
        if parsed is None:
            warnings.append(f"{where}: {field} '{_clean_str(raw)}' is not a valid number; left blank.")
        else:
            values[field] = parsed

    for field, allowed in (("status", MEMBER_STATUSES), ("termination_type", MEMBER_SEPARATION_TYPES)):
        text = _clean_str(row.get(field))
        if text is None:
            continue
        match = _match_choice(text, allowed)
        if match is None:
            errors.append(f"{where}: {field} '{text}' must be one of: {', '.join(allowed)}.")
        else:
            values[field] = match

    if include_lifetime_cap:
        raw_enabled = row.get("lifetime_cap_enabled")
        if not _is_blank(raw_enabled):
            values["lifetime_cap_enabled"] = _parse_bool(raw_enabled)
        raw_amount = row.get("lifetime_cap_amount")
        if not _is_blank(raw_amount):
            try:
                amount = _parse_decimal(raw_amount, None)
            except (TypeError, ValueError):
                amount = None
            if amount is None or amount < 0:
                errors.append(f"{where}: lifetime_cap_amount '{_clean_str(raw_amount)}' is not a valid amount.")
            else:
                values["lifetime_cap_amount"] = amount

    if member_id is None:
        return None
    return {"line": line, "member_id": member_id, "referrer_id": referrer_id, "values": values}


def _validate_members(sheet, replace=False, include_lifetime_cap=False, strict=True):
    """Check every row and the referrer tree. Returns (entries, errors, warnings).

    ``strict=False`` is for the legacy master workbook: unknown referrers are dropped and a
    blank first name falls back to the last name, each with a warning instead of an error.
    """
    errors = []
    warnings = []
    entries = []
    first_line = {}
    for line, row in zip(sheet.row_numbers, sheet.to_dict("records")):
        entry = _parse_member_row(row, line, include_lifetime_cap, errors, warnings, strict=strict)
        if entry is None:
            continue
        member_id = entry["member_id"]
        if member_id in first_line:
            errors.append(f"Row {line}: member_id {member_id} repeats row {first_line[member_id]}.")
            continue
        first_line[member_id] = line
        entries.append(entry)

    existing = {} if replace else dict(db.session.query(Member.member_id, Member.referrer_id).all())
    referrers = dict(existing)
    for entry in entries:
        member_id = entry["member_id"]
        referrer_id = entry["referrer_id"]
        where = f"Row {entry['line']} (member {member_id})"
        if referrer_id is not None and referrer_id not in first_line and referrer_id not in existing:
            message = f"{where}: referrer_id {referrer_id} is not in this file or among existing members."
            if strict:
                errors.append(message)
            else:
                warnings.append(f"{message} Imported without a referrer.")
            entry["referrer_id"] = referrer_id = None
        if referrer_id is not None or member_id not in referrers:
            referrers[member_id] = referrer_id

    for entry in entries:
        member_id = entry["member_id"]
        where = f"Row {entry['line']} (member {member_id})"
        node = referrers.get(member_id)
        for _ in range(len(referrers)):
            if node is None:
                break
            if node == member_id:
                errors.append(f"{where}: the referrer chain loops back to this member.")
                break
            node = referrers.get(node)

        entry["is_new"] = member_id not in existing
        batch = entry["values"].get("batch")
        if batch and batch > 1 and referrers.get(member_id) is None:
            warnings.append(f"{where}: batch {batch} member has no referrer_id.")

    current = _load_members([entry["member_id"] for entry in entries if not entry["is_new"]])
    for entry in entries:
        member = current.get(entry["member_id"])
        entry["changes"] = _member_changes(member, entry) if member is not None else {}
        entry["current_status"] = member.status if member is not None else None
        if entry["is_new"]:
            entry["action"] = "Add"
        else:
            entry["action"] = "Update" if entry["changes"] else "Unchanged"

    entries.sort(key=lambda item: (item["values"].get("batch") or 0, item["member_id"]))
    errors.sort(key=_issue_row)
    warnings.sort(key=_issue_row)
    return entries, errors, warnings


def _issue_row(message):
    match = re.match(r"Row (\d+)", message)
    return int(match.group(1)) if match else 0


def _load_members(member_ids, chunk_size=500):
    members = {}
    for start in range(0, len(member_ids), chunk_size):
        chunk = member_ids[start:start + chunk_size]
        for member in Member.query.filter(Member.member_id.in_(chunk)).all():
            members[member.member_id] = member
    return members


def _same_value(old, new):
    if old is None or new is None:
        return old is None and new is None
    if isinstance(old, Decimal) or isinstance(new, (Decimal, float)):
        try:
            return Decimal(str(old)) == Decimal(str(new))
        except (ArithmeticError, ValueError):
            return False
    if isinstance(old, datetime) and not isinstance(new, datetime):
        old = old.date()
    if isinstance(old, str) and isinstance(new, str):
        return old.strip() == new.strip()
    return old == new


def _member_changes(member, entry):
    """Fields whose sheet value differs from the stored value: {field: (old, new)}."""
    changes = {}
    for field, new in entry["values"].items():
        old = getattr(member, field)
        if not _same_value(old, new):
            changes[field] = (old, new)
    referrer_id = entry["referrer_id"]
    if referrer_id is not None and referrer_id != member.referrer_id:
        changes["referrer_id"] = (member.referrer_id, referrer_id)
    return changes


def _display_value(value):
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"{value:,.2f}"
    return str(value)


def preview_members_dataframe(df, limit=5, actor_role=None):
    entries, errors, warnings = _validate_members(
        df, include_lifetime_cap=is_admin_role(actor_role)
    )
    if errors:
        raise MemberImportError(errors, warnings)

    preview = []
    for entry in sorted(entries, key=lambda item: item["action"] == "Unchanged")[:limit]:
        values = entry["values"]
        preview.append({
            "member_id": entry["member_id"],
            "batch": values.get("batch"),
            "referrer_id": entry["referrer_id"],
            "status": values.get("status") or entry["current_status"] or "Active",
            "action": entry["action"],
            "changes": [
                {"field": field, "old": _display_value(old), "new": _display_value(new)}
                for field, (old, new) in entry["changes"].items()
            ],
            "date_joined": values["date_joined"].isoformat() if values.get("date_joined") else None,
            "full_name": " ".join(
                part for part in (
                    values.get("first_name"),
                    values.get("middle_name"),
                    values.get("last_name"),
                    values.get("suffix"),
                ) if part
            ),
        })
    return {
        "row_count": len(entries),
        "new_count": sum(1 for entry in entries if entry["action"] == "Add"),
        "update_count": sum(1 for entry in entries if entry["action"] == "Update"),
        "unchanged_count": sum(1 for entry in entries if entry["action"] == "Unchanged"),
        "preview": preview,
        "warnings": warnings,
    }


def import_members_dataframe(df, replace=False, actor_role=None, strict=True):
    entries, errors, warnings = _validate_members(
        df, replace=replace, include_lifetime_cap=is_admin_role(actor_role), strict=strict
    )
    if errors:
        raise MemberImportError(errors, warnings)

    counts = {"Add": 0, "Update": 0, "Unchanged": 0}
    try:
        if replace:
            clear_members_and_dependents(commit=False)

        members = {}
        with db.session.no_autoflush:
            for entry in entries:
                counts[entry["action"]] += 1
                if entry["action"] == "Unchanged":
                    continue
                if entry["is_new"]:
                    member = Member(member_id=entry["member_id"], status="Active")
                    db.session.add(member)
                    fields = entry["values"]
                else:
                    member = db.session.get(Member, entry["member_id"])
                    fields = {field: new for field, (_old, new) in entry["changes"].items()}
                    fields.pop("referrer_id", None)
                for key, value in fields.items():
                    setattr(member, key, value)
                members[entry["member_id"]] = member

        # Referrers are linked after every row exists, so file order never trips the self foreign key.
        db.session.flush()
        for entry in entries:
            member = members.get(entry["member_id"])
            if member is None or entry["referrer_id"] is None:
                continue
            if entry["is_new"] or "referrer_id" in entry["changes"]:
                member.referrer_id = entry["referrer_id"]
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        detail = str(getattr(exc, "orig", None) or exc).strip().splitlines()[0]
        raise ValueError(f"The database rejected the import; nothing was saved. {detail}") from exc

    return {
        "imported": counts["Add"],
        "updated": counts["Update"],
        "unchanged": counts["Unchanged"],
        "total": Member.query.count(),
        "warnings": warnings,
    }


def import_members_from_upload(file_storage, replace=False, actor_role=None):
    df = load_members_dataframe(file_storage)
    return import_members_dataframe(df, replace=replace, actor_role=actor_role)


def preview_members_upload(file_storage, limit=5, actor_role=None):
    df = load_members_dataframe(file_storage)
    return preview_members_dataframe(df, limit=limit, actor_role=actor_role)


def import_members_from_xlsx(path=None, replace=False, actor_role=None):
    xlsx_path = Path(path or MEMBERS_XLSX)
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Members file not found: {xlsx_path}")

    df = load_members_dataframe(xlsx_path)
    return import_members_dataframe(df, replace=replace, actor_role=actor_role, strict=False)
