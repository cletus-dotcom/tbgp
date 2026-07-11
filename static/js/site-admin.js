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
        gallery: `
            <div class="repeater-item">
                <div class="row g-2">
                    <div class="col-md-7">
                        <label class="form-label">Image URL</label>
                        <input class="form-control" data-field="url">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Alt text</label>
                        <input class="form-control" data-field="alt">
                    </div>
                    <div class="col-md-1 d-flex align-items-end">
                        <button type="button" class="btn btn-outline-danger btn-sm repeater-remove">&times;</button>
                    </div>
                </div>
            </div>`,
    };

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
            if (!list || !repeaterTemplates[prefix]) {
                return;
            }
            list.insertAdjacentHTML("beforeend", repeaterTemplates[prefix]);
            reindexRepeater(list);
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
    const partnerForm = document.querySelector(".site-admin-form");

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
})();
