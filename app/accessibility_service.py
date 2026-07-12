"""Accessibility preferences — text size, high contrast, user sync."""

from app import db
from app.models import User

TEXT_SIZES = ("standard", "large", "xlarge")
DEFAULT_ACCESSIBILITY_PREFS = {
    "text_size": "standard",
    "high_contrast": False,
}


def normalize_accessibility_prefs(data=None):
    payload = data or {}
    text_size = (payload.get("text_size") or "standard").strip().lower()
    if text_size not in TEXT_SIZES:
        text_size = "standard"
    return {
        "text_size": text_size,
        "high_contrast": bool(payload.get("high_contrast")),
    }


def get_user_accessibility_prefs(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return normalize_accessibility_prefs(DEFAULT_ACCESSIBILITY_PREFS)
    return normalize_accessibility_prefs({
        "text_size": getattr(user, "comfort_text_size", None) or "standard",
        "high_contrast": bool(getattr(user, "comfort_high_contrast", False)),
    })


def save_user_accessibility_prefs(user_id, data):
    user = db.session.get(User, user_id)
    if user is None:
        raise ValueError("User not found.")

    prefs = normalize_accessibility_prefs(data)
    user.comfort_text_size = prefs["text_size"]
    user.comfort_high_contrast = prefs["high_contrast"]
    db.session.add(user)
    db.session.commit()
    return prefs
