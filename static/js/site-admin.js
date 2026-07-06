(function () {
    const menuToggle = document.getElementById("menuToggle");
    const sidebar = document.getElementById("sidebar");
    if (menuToggle && sidebar) {
        menuToggle.addEventListener("click", function () {
            sidebar.classList.toggle("open");
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
})();
