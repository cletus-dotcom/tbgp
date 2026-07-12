(function () {
    const STORAGE_KEY = "tbgp_accessibility";
    const API_URL = document.body && document.body.dataset.accessibilityApiUrl;

    function normalizePrefs(prefs) {
        const textSize = prefs && prefs.text_size ? String(prefs.text_size).toLowerCase() : "standard";
        const allowed = { standard: true, large: true, xlarge: true };
        return {
            text_size: allowed[textSize] ? textSize : "standard",
            high_contrast: Boolean(prefs && prefs.high_contrast),
        };
    }

    function readLocalPrefs() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) {
                return null;
            }
            return normalizePrefs(JSON.parse(raw));
        } catch (error) {
            return null;
        }
    }

    function writeLocalPrefs(prefs) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
        } catch (error) {
            /* ignore */
        }
    }

    function applyPrefs(prefs) {
        const normalized = normalizePrefs(prefs);
        const html = document.documentElement;
        html.classList.remove(
            "comfort-view",
            "comfort-text-large",
            "comfort-text-xlarge",
            "comfort-high-contrast"
        );
        if (normalized.text_size === "large") {
            html.classList.add("comfort-text-large");
        } else if (normalized.text_size === "xlarge") {
            html.classList.add("comfort-text-xlarge");
        }
        if (normalized.high_contrast) {
            html.classList.add("comfort-high-contrast");
        }
        return normalized;
    }

    function prefsSummary(prefs) {
        const sizeLabels = {
            standard: "Standard text",
            large: "Large text",
            xlarge: "Extra large text",
        };
        const parts = [sizeLabels[prefs.text_size] || "Standard text"];
        if (prefs.high_contrast) {
            parts.push("high contrast on");
        }
        return parts.join(", ") + ".";
    }

    function isPanelOpen() {
        const panel = document.getElementById("comfortViewPanel");
        return panel && !panel.hidden;
    }

    function setPanelOpen(open) {
        const panel = document.getElementById("comfortViewPanel");
        if (!panel) {
            return;
        }
        panel.hidden = !open;
        document.querySelectorAll("[data-comfort-view-open]").forEach(function (button) {
            button.setAttribute("aria-expanded", open ? "true" : "false");
            button.classList.toggle("is-active", open || !isDefaultPrefs(getCurrentFormPrefs()));
        });
        if (open) {
            const first = panel.querySelector("input[data-comfort-text-size]:checked");
            if (first) {
                first.focus();
            }
        }
    }

    function isDefaultPrefs(prefs) {
        return prefs.text_size === "standard" && !prefs.high_contrast;
    }

    function getCurrentFormPrefs() {
        const panel = document.getElementById("comfortViewPanel");
        if (!panel) {
            return normalizePrefs({});
        }
        const selected = panel.querySelector('input[data-comfort-text-size]:checked');
        const highContrast = panel.querySelector("[data-comfort-high-contrast]");
        return normalizePrefs({
            text_size: selected ? selected.value : "standard",
            high_contrast: highContrast ? highContrast.checked : false,
        });
    }

    function syncForm(prefs) {
        const panel = document.getElementById("comfortViewPanel");
        if (!panel) {
            return;
        }
        const normalized = normalizePrefs(prefs);
        panel.querySelectorAll("[data-comfort-text-size]").forEach(function (input) {
            input.checked = input.value === normalized.text_size;
        });
        const highContrast = panel.querySelector("[data-comfort-high-contrast]");
        if (highContrast) {
            highContrast.checked = normalized.high_contrast;
        }
        syncToggleButtons(normalized);
    }

    function syncToggleButtons(prefs) {
        const active = !isDefaultPrefs(prefs);
        document.querySelectorAll("[data-comfort-view-open]").forEach(function (button) {
            button.classList.toggle("is-active", active || isPanelOpen());
            const label = button.querySelector(".comfort-view-toggle-label");
            if (label) {
                label.textContent = active ? "Reading on" : "Reading";
            }
            button.setAttribute(
                "aria-label",
                active
                    ? "Reading settings active. Open reading and contrast settings."
                    : "Open reading and contrast settings"
            );
        });
        const status = document.getElementById("comfortViewStatus");
        if (status) {
            status.textContent = active
                ? "Reading settings updated: " + prefsSummary(prefs)
                : "Standard reading settings.";
        }
    }

    function savePrefs(prefs) {
        const normalized = applyPrefs(prefs);
        writeLocalPrefs(normalized);
        syncForm(normalized);

        if (!API_URL) {
            return Promise.resolve(normalized);
        }

        return fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify(normalized),
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Could not save to your account.");
                }
                return response.json();
            })
            .then(function (payload) {
                const saved = normalizePrefs(payload);
                applyPrefs(saved);
                writeLocalPrefs(saved);
                syncForm(saved);
                return saved;
            })
            .catch(function () {
                const status = document.getElementById("comfortViewStatus");
                if (status) {
                    status.textContent =
                        "Settings applied on this device. Account sync failed; try again later.";
                }
                return normalized;
            });
    }

    function loadInitialPrefs() {
        const local = readLocalPrefs();
        if (local) {
            syncForm(local);
            return Promise.resolve(local);
        }
        if (window.TBGP_SERVER_A11Y_PREFS) {
            const server = normalizePrefs(window.TBGP_SERVER_A11Y_PREFS);
            applyPrefs(server);
            writeLocalPrefs(server);
            syncForm(server);
            return Promise.resolve(server);
        }
        if (!API_URL) {
            syncForm(normalizePrefs({}));
            return Promise.resolve(normalizePrefs({}));
        }
        return fetch(API_URL, { credentials: "same-origin" })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("fetch failed");
                }
                return response.json();
            })
            .then(function (payload) {
                const prefs = normalizePrefs(payload);
                applyPrefs(prefs);
                writeLocalPrefs(prefs);
                syncForm(prefs);
                return prefs;
            })
            .catch(function () {
                syncForm(normalizePrefs({}));
                return normalizePrefs({});
            });
    }

    function handleFormChange() {
        savePrefs(getCurrentFormPrefs());
    }

    document.addEventListener("click", function (event) {
        const openBtn = event.target.closest("[data-comfort-view-open]");
        if (openBtn) {
            event.preventDefault();
            setPanelOpen(!isPanelOpen());
            return;
        }

        const closeBtn = event.target.closest("[data-comfort-view-close]");
        if (closeBtn) {
            setPanelOpen(false);
            document.querySelector("[data-comfort-view-open]")?.focus();
            return;
        }

        const panel = document.getElementById("comfortViewPanel");
        if (panel && isPanelOpen() && !event.target.closest(".comfort-view-panel, [data-comfort-view-open]")) {
            setPanelOpen(false);
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && isPanelOpen()) {
            setPanelOpen(false);
            document.querySelector("[data-comfort-view-open]")?.focus();
        }
    });

    document.addEventListener("change", function (event) {
        if (
            event.target.matches("[data-comfort-text-size]") ||
            event.target.matches("[data-comfort-high-contrast]")
        ) {
            handleFormChange();
        }
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", loadInitialPrefs);
    } else {
        loadInitialPrefs();
    }
})();
