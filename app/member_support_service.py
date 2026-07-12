import re
from urllib.parse import quote

MEMBER_SUPPORT_SUBJECTS = (
    {
        "value": "membership",
        "label": "Membership Concern",
        "env_key": "MEMBER_WHATSAPP_MEMBERSHIP",
    },
    {
        "value": "other",
        "label": "Other Matters",
        "env_key": "MEMBER_WHATSAPP_OTHER_MATTERS",
    },
)


def normalize_whatsapp_digits(value):
    digits = re.sub(r"\D", "", (value or "").strip())
    if not digits:
        return ""
    if digits.startswith("63"):
        return digits
    if digits.startswith("0"):
        return f"63{digits[1:]}"
    return digits


def member_support_subjects():
    from app.config import MEMBER_WHATSAPP_MEMBERSHIP, MEMBER_WHATSAPP_OTHER_MATTERS

    numbers = {
        "membership": normalize_whatsapp_digits(MEMBER_WHATSAPP_MEMBERSHIP),
        "other": normalize_whatsapp_digits(MEMBER_WHATSAPP_OTHER_MATTERS),
    }
    subjects = []
    for item in MEMBER_SUPPORT_SUBJECTS:
        subjects.append({
            "value": item["value"],
            "label": item["label"],
            "whatsapp": numbers[item["value"]],
        })
    return subjects


def member_support_configured():
    return any(subject["whatsapp"] for subject in member_support_subjects())


def build_member_support_message(subject_value, details, member_id=None, member_name=""):
    subjects = {item["value"]: item["label"] for item in MEMBER_SUPPORT_SUBJECTS}
    subject_label = subjects.get(subject_value, subject_value)
    lines = [
        "TBGP Member Portal",
        f"Subject: {subject_label}",
    ]
    if member_id:
        member_line = f"Member: #{member_id}"
        if member_name:
            member_line += f" — {member_name}"
        lines.append(member_line)
    lines.append("")
    lines.append("Details:")
    lines.append(details.strip())
    return "\n".join(lines)


def build_member_support_whatsapp_url(subject_value, details, member_id=None, member_name=""):
    numbers = {item["value"]: item["whatsapp"] for item in member_support_subjects()}
    whatsapp = numbers.get(subject_value, "")
    if not whatsapp:
        raise ValueError("WhatsApp support is not configured for the selected subject.")
    message = build_member_support_message(
        subject_value,
        details,
        member_id=member_id,
        member_name=member_name,
    )
    return f"https://wa.me/{whatsapp}?text={quote(message)}"
