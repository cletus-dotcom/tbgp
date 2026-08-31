"""Landing page gallery folders and images."""

from __future__ import annotations

import re
from datetime import datetime

from app import db
from app.models import CmsGalleryFolder

GALLERY_STATUS_DRAFT = "draft"
GALLERY_STATUS_PUBLISHED = "published"
GALLERY_STATUSES = (GALLERY_STATUS_DRAFT, GALLERY_STATUS_PUBLISHED)


def _normalize_slug(value):
    slug = re.sub(r"[^a-z0-9-]+", "-", (value or "").lower()).strip("-")
    return slug or "gallery-folder"


def _parse_images(form):
    images = []
    for key in sorted(form.keys()):
        if not key.startswith("gallery_url_"):
            continue
        url = (form.get(key) or "").strip()
        if not url:
            continue
        idx = key.replace("gallery_url_", "", 1)
        alt = (form.get(f"gallery_alt_{idx}") or "").strip()
        images.append({"url": url, "alt": alt})
    return images


def list_folders_for_admin():
    return (
        CmsGalleryFolder.query
        .order_by(
            CmsGalleryFolder.sort_order.asc(),
            CmsGalleryFolder.title.asc(),
            CmsGalleryFolder.folder_id.asc(),
        )
        .all()
    )


def list_published_folders():
    return (
        CmsGalleryFolder.query
        .filter_by(status=GALLERY_STATUS_PUBLISHED)
        .order_by(
            CmsGalleryFolder.sort_order.asc(),
            CmsGalleryFolder.title.asc(),
            CmsGalleryFolder.folder_id.asc(),
        )
        .all()
    )


def get_folder(folder_id=None, slug=None):
    if folder_id is not None:
        return db.session.get(CmsGalleryFolder, int(folder_id))
    if slug:
        return CmsGalleryFolder.query.filter_by(slug=slug).first()
    return None


def parse_folder_form(form, existing=None):
    title = (form.get("title") or "").strip()
    if not title:
        raise ValueError("Folder title is required.")

    slug_input = (form.get("slug") or "").strip()
    slug = _normalize_slug(slug_input or title)
    if existing and slug != existing.slug:
        conflict = CmsGalleryFolder.query.filter(
            CmsGalleryFolder.slug == slug,
            CmsGalleryFolder.folder_id != existing.folder_id,
        ).first()
        if conflict:
            raise ValueError("Another gallery folder already uses that URL slug.")
    elif not existing:
        conflict = CmsGalleryFolder.query.filter_by(slug=slug).first()
        if conflict:
            raise ValueError("Another gallery folder already uses that URL slug.")

    status = (form.get("status") or GALLERY_STATUS_DRAFT).strip().lower()
    if status not in GALLERY_STATUSES:
        status = GALLERY_STATUS_DRAFT

    try:
        sort_order = int(form.get("sort_order") or 0)
    except (TypeError, ValueError):
        sort_order = 0

    return {
        "slug": slug,
        "title": title,
        "description": (form.get("description") or "").strip(),
        "status": status,
        "sort_order": sort_order,
        "images": _parse_images(form),
    }


def save_folder(data, folder=None):
    if folder is None:
        folder = CmsGalleryFolder()
    folder.slug = data["slug"]
    folder.title = data["title"]
    folder.description = data.get("description") or ""
    folder.status = data.get("status") or GALLERY_STATUS_DRAFT
    folder.sort_order = data.get("sort_order") or 0
    folder.images = data.get("images") or []
    folder.updated_at = datetime.utcnow()
    db.session.add(folder)
    db.session.commit()
    return folder


def delete_folder(folder_id):
    folder = get_folder(folder_id=folder_id)
    if folder is None:
        return False
    db.session.delete(folder)
    db.session.commit()
    return True
