import mimetypes
import re
import uuid
from pathlib import Path

from flask import current_app
from werkzeug.datastructures import FileStorage

from app.config import (
    SUPABASE_PARTNER_IMAGES_BUCKET,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
    supabase_storage_configured,
)

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
MAX_PARTNER_IMAGE_BYTES = 5 * 1024 * 1024
PARTNER_IMAGE_KINDS = {"thumb", "logo", "gallery"}


def _get_supabase_client():
    if not supabase_storage_configured():
        raise RuntimeError(
            "Supabase Storage is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )
    from supabase import create_client

    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def _normalize_partner_slug(slug):
    value = re.sub(r"[^a-z0-9-]+", "-", (slug or "").lower()).strip("-")
    return value or "draft"


def _extension_for_upload(filename, content_type):
    ext = Path(filename or "").suffix.lower()
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        return ext
    guessed = mimetypes.guess_extension((content_type or "").split(";", 1)[0].strip())
    if guessed and guessed.lower() in ALLOWED_IMAGE_EXTENSIONS:
        return guessed.lower()
    return ".jpg"


def _validate_image_upload(file_storage):
    if file_storage is None or not file_storage.filename:
        raise ValueError("Choose an image file to upload.")

    content_type = (file_storage.mimetype or "").split(";", 1)[0].strip().lower()
    if content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValueError("Only JPEG, PNG, WebP, and GIF images are allowed.")

    payload = file_storage.read()
    file_storage.stream.seek(0)
    if not payload:
        raise ValueError("The selected file is empty.")
    if len(payload) > MAX_PARTNER_IMAGE_BYTES:
        raise ValueError("Image must be 5 MB or smaller.")

    return payload, content_type


def upload_partner_image(file_storage, partner_slug, image_kind):
    image_kind = (image_kind or "gallery").strip().lower()
    if image_kind not in PARTNER_IMAGE_KINDS:
        raise ValueError("Invalid image type.")

    payload, content_type = _validate_image_upload(file_storage)
    slug = _normalize_partner_slug(partner_slug)
    extension = _extension_for_upload(file_storage.filename, content_type)
    object_name = f"{slug}/{image_kind}-{uuid.uuid4().hex}{extension}"

    client = _get_supabase_client()
    bucket = current_app.config.get(
        "SUPABASE_PARTNER_IMAGES_BUCKET",
        SUPABASE_PARTNER_IMAGES_BUCKET,
    )
    storage = client.storage.from_(bucket)
    storage.upload(
        object_name,
        payload,
        file_options={
            "content-type": content_type,
            "cache-control": "3600",
            "upsert": "false",
        },
    )
    public_url = storage.get_public_url(object_name)
    return {
        "url": public_url,
        "path": object_name,
        "kind": image_kind,
    }
