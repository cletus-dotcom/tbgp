(function () {
    const menuToggle = document.getElementById("menuToggle");
    const sidebar = document.getElementById("sidebar");
    const body = document.body;
    const isDesktop = () => window.matchMedia("(min-width: 992px)").matches;

    function closeSidebar() {
        if (!sidebar || isDesktop()) {
            return;
        }
        sidebar.classList.remove("visible");
        body.classList.remove("no-scroll", "sidebar-open");
        menuToggle?.setAttribute("aria-expanded", "false");
    }

    if (menuToggle && sidebar) {
        menuToggle.addEventListener("click", function (e) {
            e.stopPropagation();
            if (isDesktop()) {
                return;
            }
            const isOpen = sidebar.classList.toggle("visible");
            body.classList.toggle("no-scroll", isOpen);
            body.classList.toggle("sidebar-open", isOpen);
            menuToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
        });

        document.addEventListener("click", function (e) {
            if (isDesktop()) {
                return;
            }
            const clickInside = sidebar.contains(e.target) || menuToggle.contains(e.target);
            if (!clickInside) {
                closeSidebar();
            }
        });
    }

    const repeaterTemplates = {
        highlight: `
            <div class="repeater-item">
                <div class="row g-2">
                    <div class="col-md-1">
                        <label class="form-label">Icon</label>
                        <input class="form-control" data-field="icon">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Title</label>
                        <input class="form-control" data-field="title">
                    </div>
                    <div class="col-md-7">
                        <label class="form-label">Body</label>
                        <textarea class="form-control" data-field="body" rows="2"></textarea>
                    </div>
                    <div class="col-md-1 d-flex align-items-end">
                        <button type="button" class="btn btn-outline-danger btn-sm repeater-remove">&times;</button>
                    </div>
                </div>
            </div>`,
        landing_bullet: `
            <div class="repeater-item">
                <div class="row g-2">
                    <div class="col-md-1">
                        <label class="form-label">Icon</label>
                        <input class="form-control" data-field="icon">
                    </div>
                    <div class="col-md-10">
                        <label class="form-label">Bullet text</label>
                        <input class="form-control" data-field="text">
                    </div>
                    <div class="col-md-1 d-flex align-items-end">
                        <button type="button" class="btn btn-outline-danger btn-sm repeater-remove">&times;</button>
                    </div>
                </div>
            </div>`,
    };

    function galleryRepeaterTemplate() {
        const form = document.querySelector(".site-admin-form[data-partner-image-upload-enabled]");
        const uploadEnabled = form?.dataset.partnerImageUploadEnabled === "true";
        const uploadBlock = uploadEnabled
            ? `
                        <div class="partner-image-actions">
                            <input type="file" class="partner-image-file" accept="image/jpeg,image/png,image/webp,image/gif" hidden>
                            <button type="button" class="btn btn-outline-primary btn-sm partner-image-upload-btn">
                                <i class="bi bi-upload"></i> Upload
                            </button>
                            <span class="partner-image-status text-muted small"></span>
                        </div>`
            : "";

        return `
            <div class="repeater-item">
                <div class="row g-2">
                    <div class="col-md-7">
                        <label class="form-label">Image</label>
                        <div class="partner-image-field partner-image-field-inline" data-image-kind="gallery">
                            <input class="form-control partner-image-url" data-field="url" placeholder="https://... or upload below">
                            ${uploadBlock}
                        </div>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Alt text</label>
                        <input class="form-control" data-field="alt">
                    </div>
                    <div class="col-md-1 d-flex align-items-end">
                        <button type="button" class="btn btn-outline-danger btn-sm repeater-remove">&times;</button>
                    </div>
                </div>
            </div>`;
    }

    function reindexRepeater(list) {
        const prefix = list.dataset.repeater;
        const fields = (list.dataset.fields || "").split(",");
        list.querySelectorAll(".repeater-item").forEach(function (item, index) {
            fields.forEach(function (field) {
                const input = item.querySelector('[data-field="' + field + '"], [name^="' + prefix + '_' + field + '_"]');
                if (!input) {
                    return;
                }
                input.name = prefix + "_" + field + "_" + index;
                if (!input.hasAttribute("data-field")) {
                    input.setAttribute("data-field", field);
                }
            });
        });
    }

    document.querySelectorAll(".repeater-list").forEach(function (list) {
        reindexRepeater(list);
    });

    document.addEventListener("click", function (event) {
        const addBtn = event.target.closest(".repeater-add");
        if (addBtn) {
            const prefix = addBtn.dataset.target;
            const list = addBtn.previousElementSibling;
            if (!list) {
                return;
            }
            let html = "";
            if (prefix === "gallery") {
                html = galleryRepeaterTemplate();
            } else if (repeaterTemplates[prefix]) {
                html = repeaterTemplates[prefix];
            }
            if (!html) {
                return;
            }
            list.insertAdjacentHTML("beforeend", html);
            reindexRepeater(list);
            list.querySelectorAll(".repeater-item:last-child .partner-image-field").forEach(wirePartnerImageField);
            return;
        }

        const removeBtn = event.target.closest(".repeater-remove");
        if (removeBtn) {
            const item = removeBtn.closest(".repeater-item");
            const list = item && item.parentElement;
            if (item && list && list.classList.contains("repeater-list")) {
                item.remove();
                reindexRepeater(list);
            }
        }
    });

    const partnerTypeSelect = document.getElementById("partner_type");
    const portalLinkFields = document.querySelectorAll(".portal-link-field");
    const portalSyncedFields = document.querySelectorAll(".portal-synced-field");
    const portalSyncedNotes = document.querySelectorAll(".portal-synced-note");
    const partnerForm = document.querySelector(".site-admin-form[data-partner-image-upload-enabled], .site-admin-form[data-portal-linked]");

    function syncPortalLinkFields() {
        if (!partnerTypeSelect) {
            return;
        }
        const partnerType = partnerTypeSelect.value;
        const showContractor = partnerType === "contractors";
        const showSupplier = partnerType === "suppliers";

        document.querySelectorAll(".portal-contractor-field").forEach(function (el) {
            el.hidden = !showContractor;
        });
        document.querySelectorAll(".portal-supplier-field").forEach(function (el) {
            el.hidden = !showSupplier;
        });
        const preview = document.getElementById("portal-link-preview");
        if (preview) {
            preview.hidden = !showContractor && !showSupplier;
        }

        const portalContractorInput = document.getElementById("portal_contractor_id");
        if (portalContractorInput) {
            portalContractorInput.disabled = !showContractor;
        }
        const portalSupplierInput = document.getElementById("portal_supplier_id");
        if (portalSupplierInput) {
            portalSupplierInput.disabled = !showSupplier;
        }
        syncPortalSyncedFields();
    }

    function syncPortalSyncedFields() {
        const isContractor = partnerTypeSelect?.value === "contractors";
        const isSupplier = partnerTypeSelect?.value === "suppliers";
        const portalLinked = partnerForm?.dataset.portalLinked === "true";
        const lock = portalLinked && (isContractor || isSupplier);

        portalSyncedFields.forEach(function (el) {
            el.readOnly = lock;
            if (el.id === "name") {
                el.required = !lock;
            }
        });
        portalSyncedNotes.forEach(function (el) {
            el.hidden = !lock;
        });
    }

    if (partnerTypeSelect) {
        partnerTypeSelect.addEventListener("change", syncPortalLinkFields);
        syncPortalLinkFields();
    } else {
        syncPortalSyncedFields();
    }

    function updatePartnerImagePreview(field, url) {
        const preview = field.querySelector(".partner-image-preview");
        const empty = field.querySelector(".partner-image-preview-empty");
        if (!preview) {
            return;
        }
        if (url) {
            preview.src = url;
            preview.hidden = false;
            if (empty) {
                empty.hidden = true;
            }
        } else {
            preview.removeAttribute("src");
            preview.hidden = true;
            if (empty) {
                empty.hidden = false;
            }
        }
    }

    function setPartnerImageStatus(field, message, isError) {
        const status = field.querySelector(".partner-image-status");
        if (!status) {
            return;
        }
        status.textContent = message || "";
        status.classList.toggle("text-danger", Boolean(isError));
        status.classList.toggle("text-muted", !isError);
    }

    function uploadPartnerImage(field, file) {
        const uploadUrl = partnerForm?.dataset.partnerImageUploadUrl;
        if (!uploadUrl || !file) {
            return;
        }

        const slugInput = document.getElementById("slug");
        const slug = (slugInput && slugInput.value.trim()) || "draft";
        const kind = field.dataset.imageKind || "gallery";
        const urlInput = field.querySelector(".partner-image-url");
        const uploadBtn = field.querySelector(".partner-image-upload-btn");
        const formData = new FormData();

        formData.append("file", file);
        formData.append("slug", slug);
        formData.append("kind", kind);

        if (uploadBtn) {
            uploadBtn.disabled = true;
        }
        setPartnerImageStatus(field, "Uploading...", false);

        fetch(uploadUrl, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
        })
            .then(function (response) {
                return response.json().then(function (payload) {
                    if (!response.ok) {
                        throw new Error(payload.error || "Upload failed.");
                    }
                    return payload;
                });
            })
            .then(function (payload) {
                if (urlInput) {
                    urlInput.value = payload.url;
                    urlInput.dispatchEvent(new Event("input", { bubbles: true }));
                }
                updatePartnerImagePreview(field, payload.url);
                setPartnerImageStatus(field, "Uploaded.", false);
            })
            .catch(function (error) {
                setPartnerImageStatus(field, error.message || "Upload failed.", true);
            })
            .finally(function () {
                if (uploadBtn) {
                    uploadBtn.disabled = false;
                }
            });
    }

    function wirePartnerImageField(field) {
        const urlInput = field.querySelector(".partner-image-url");
        const fileInput = field.querySelector(".partner-image-file");
        const uploadBtn = field.querySelector(".partner-image-upload-btn");

        if (urlInput && !urlInput.dataset.previewWired) {
            urlInput.dataset.previewWired = "true";
            urlInput.addEventListener("input", function () {
                updatePartnerImagePreview(field, urlInput.value.trim());
            });
        }

        if (uploadBtn && fileInput && !uploadBtn.dataset.uploadWired) {
            uploadBtn.dataset.uploadWired = "true";
            uploadBtn.addEventListener("click", function () {
                fileInput.click();
            });
            fileInput.addEventListener("change", function () {
                const file = fileInput.files && fileInput.files[0];
                if (!file) {
                    return;
                }
                uploadPartnerImage(field, file);
                fileInput.value = "";
            });
        }
    }

    document.querySelectorAll(".partner-image-field").forEach(wirePartnerImageField);
})();
