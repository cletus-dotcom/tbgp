/**
 * Searchable member select for portal forms.
 * members: [{ id, label, search }]
 */
(function (global) {
    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function initMemberSearchSelect(fieldId, members, options) {
        const root = document.querySelector(`[data-member-search-select="${fieldId}"]`);
        if (!root) return null;

        const hidden = document.getElementById(fieldId);
        const input = document.getElementById(`${fieldId}Display`);
        const list = document.getElementById(`${fieldId}List`);
        const clearBtn = root.querySelector(`[data-clear-for="${fieldId}"]`);
        const opts = options || {};
        const limit = opts.limit || 40;
        let open = false;
        let activeIndex = -1;
        let filtered = [];

        function setOpen(next) {
            open = next;
            list.classList.toggle('d-none', !open);
            list.hidden = !open;
            input.setAttribute('aria-expanded', open ? 'true' : 'false');
            root.classList.toggle('is-open', open);
        }

        function syncClear() {
            clearBtn?.classList.toggle('d-none', !hidden.value);
        }

        function selectMember(member) {
            if (!member) return;
            hidden.value = String(member.id);
            input.value = member.label;
            syncClear();
            setOpen(false);
            activeIndex = -1;
            hidden.dispatchEvent(new Event('change', { bubbles: true }));
            if (typeof opts.onChange === 'function') opts.onChange(member);
        }

        function clearSelection() {
            hidden.value = '';
            input.value = '';
            syncClear();
            setOpen(false);
            activeIndex = -1;
            hidden.dispatchEvent(new Event('change', { bubbles: true }));
            if (typeof opts.onChange === 'function') opts.onChange(null);
            input.focus();
        }

        function renderList(query) {
            const q = String(query || '').trim().toLowerCase();
            filtered = members.filter((m) => {
                if (!q) return true;
                return (m.search || '').includes(q) || String(m.id).includes(q);
            }).slice(0, limit);

            if (!filtered.length) {
                list.innerHTML = `<div class="member-search-empty">No members match “${escapeHtml(query)}”.</div>`;
                activeIndex = -1;
                return;
            }

            list.innerHTML = filtered.map((m, idx) => `
                <button type="button"
                        class="member-search-option${idx === activeIndex ? ' is-active' : ''}"
                        role="option"
                        data-index="${idx}"
                        data-id="${m.id}"
                        aria-selected="${idx === activeIndex ? 'true' : 'false'}">
                    <span class="member-search-option-label">${escapeHtml(m.label)}</span>
                    <span class="member-search-option-meta">ID ${escapeHtml(m.id)} · Batch ${escapeHtml(m.batch)}</span>
                </button>
            `).join('');
        }

        function openAndFilter() {
            renderList(input.value);
            setOpen(true);
        }

        input.addEventListener('focus', () => openAndFilter());
        input.addEventListener('click', () => openAndFilter());
        input.addEventListener('input', () => {
            if (hidden.value) {
                const current = members.find((m) => String(m.id) === String(hidden.value));
                if (!current || input.value !== current.label) {
                    hidden.value = '';
                    syncClear();
                    hidden.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
            activeIndex = 0;
            openAndFilter();
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (!open) openAndFilter();
                activeIndex = Math.min(activeIndex + 1, filtered.length - 1);
                renderList(input.value);
                list.querySelector('.member-search-option.is-active')?.scrollIntoView({ block: 'nearest' });
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                activeIndex = Math.max(activeIndex - 1, 0);
                renderList(input.value);
                list.querySelector('.member-search-option.is-active')?.scrollIntoView({ block: 'nearest' });
            } else if (e.key === 'Enter') {
                if (open && activeIndex >= 0 && filtered[activeIndex]) {
                    e.preventDefault();
                    selectMember(filtered[activeIndex]);
                }
            } else if (e.key === 'Escape') {
                setOpen(false);
            }
        });

        list.addEventListener('mousedown', (e) => {
            const option = e.target.closest('.member-search-option');
            if (!option) return;
            e.preventDefault();
            const member = filtered[Number(option.dataset.index)];
            selectMember(member);
        });

        clearBtn?.addEventListener('click', (e) => {
            e.preventDefault();
            clearSelection();
        });

        document.addEventListener('click', (e) => {
            if (!root.contains(e.target)) setOpen(false);
        });

        syncClear();
        return {
            getValue: () => hidden.value,
            setValue: (id) => {
                const member = members.find((m) => String(m.id) === String(id));
                if (member) selectMember(member);
                else clearSelection();
            },
            clear: clearSelection,
        };
    }

    global.initMemberSearchSelect = initMemberSearchSelect;
})(window);
