import logging
import mimetypes
import re
import uuid
from pathlib import Path

from flask import current_app

from app.config import (
    SUPABASE_PARTNER_IMAGES_BUCKET,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
    supabase_storage_config_error,
    supabase_storage_configured,
)

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
MAX_PARTNER_IMAGE_BYTES = 5 * 1024 * 1024
PARTNER_IMAGE_KINDS = {"thumb", "logo", "gallery"}
MARKETPLACE_IMAGE_KINDS = {"thumb", "gallery", "hero"}


def _get_supabase_client():
    config_error = supabase_storage_config_error()
    if config_error:
        raise RuntimeError(config_error)
    if not supabase_storage_configured():
        raise RuntimeError(
            "Supabase Storage is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )
    from supabase import create_client, ClientOptions

    return create_client(
        SUPABASE_URL,
        SUPABASE_SERVICE_ROLE_KEY,
        options=ClientOptions(storage_client_timeout=120),
    )


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


def _bucket_name():
    return current_app.config.get(
        "SUPABASE_PARTNER_IMAGES_BUCKET",
        SUPABASE_PARTNER_IMAGES_BUCKET,
    )


def _ensure_partner_images_bucket(client, bucket):
    """Create the public partner-images bucket if it does not exist yet."""
    try:
        client.storage.get_bucket(bucket)
        return
    except Exception:
        pass

    try:
        client.storage.create_bucket(
            bucket,
            options={
                "public": True,
                "file_size_limit": MAX_PARTNER_IMAGE_BYTES,
                "allowed_mime_types": sorted(ALLOWED_IMAGE_MIME_TYPES),
            },
        )
        logger.info("Created Supabase Storage bucket %s", bucket)
    except Exception as exc:
        # Race or already exists after get_bucket failed for another reason.
        message = str(exc).lower()
        if "already exists" in message or "duplicate" in message:
            return
        try:
            client.storage.get_bucket(bucket)
            return
        except Exception:
            raise RuntimeError(
                f"Supabase bucket '{bucket}' is missing and could not be created: {exc}"
            ) from exc


def _storage_error_message(exc):
    text = str(exc).strip() or exc.__class__.__name__
    lower = text.lower()
    if "bucket" in lower and ("not found" in lower or "does not exist" in lower):
        return (
            f"Storage bucket '{_bucket_name()}' was not found. "
            "Create it in Supabase Storage or re-run migrations/supabase_partner_images_bucket.sql."
        )
    if "jwt" in lower or "api key" in lower or "unauthorized" in lower or "403" in lower:
        return (
            "Supabase rejected the upload credentials. "
            "Confirm SUPABASE_URL is https://YOUR_REF.supabase.co and "
            "SUPABASE_SERVICE_ROLE_KEY is the service_role secret."
        )
    if "row-level security" in lower or "violates" in lower or "42501" in lower:
        return (
            "Storage policy blocked the upload. "
            "Run migrations/supabase_partner_images_bucket.sql in the Supabase SQL Editor."
        )
    # Keep response short for the UI.
    if len(text) > 220:
        text = text[:217] + "..."
    return f"Image upload failed: {text}"


def _upload_bytes(object_name, payload, content_type, image_kind):
    client = _get_supabase_client()
    bucket = _bucket_name()
    _ensure_partner_images_bucket(client, bucket)
    storage = client.storage.from_(bucket)
    try:
        storage.upload(
            object_name,
            payload,
            file_options={
                "content-type": content_type,
                "cache-control": "3600",
                "upsert": "false",
            },
        )
    except Exception as exc:
        logger.exception("Supabase Storage upload failed for %s/%s", bucket, object_name)
        raise RuntimeError(_storage_error_message(exc)) from exc

    public_url = storage.get_public_url(object_name)
    if isinstance(public_url, str):
        public_url = public_url.rstrip("?")
    return {
        "url": public_url,
        "path": object_name,
        "kind": image_kind,
    }


def upload_partner_image(file_storage, partner_slug, image_kind):
    image_kind = (image_kind or "gallery").strip().lower()
    if image_kind not in PARTNER_IMAGE_KINDS:
        raise ValueError("Invalid image type.")

    payload, content_type = _validate_image_upload(file_storage)
    slug = _normalize_partner_slug(partner_slug)
    extension = _extension_for_upload(file_storage.filename, content_type)
    object_name = f"{slug}/{image_kind}-{uuid.uuid4().hex}{extension}"
    return _upload_bytes(object_name, payload, content_type, image_kind)


def upload_marketplace_image(file_storage, listing_key, image_kind):
    """Upload marketplace thumb/gallery/hero image into the partner images bucket under marketplace/."""
    image_kind = (image_kind or "gallery").strip().lower()
    if image_kind not in MARKETPLACE_IMAGE_KINDS:
        raise ValueError("Invalid image type.")

    payload, content_type = _validate_image_upload(file_storage)
    key = _normalize_partner_slug(listing_key)
    extension = _extension_for_upload(file_storage.filename, content_type)
    object_name = f"marketplace/{key}/{image_kind}-{uuid.uuid4().hex}{extension}"
    return _upload_bytes(object_name, payload, content_type, image_kind)
