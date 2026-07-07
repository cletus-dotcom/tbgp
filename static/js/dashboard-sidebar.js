(function () {
    "use strict";

    document.querySelectorAll(".sidebar-section-toggle").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            var targetId = btn.getAttribute("data-target");
            var chevronId = btn.getAttribute("data-chevron");
            var sub = targetId ? document.getElementById(targetId) : null;
            var chevron = chevronId ? document.getElementById(chevronId) : null;
            if (!sub) {
                return;
            }

            var opening = sub.classList.contains("d-none");
            sub.classList.toggle("d-none");
            btn.setAttribute("aria-expanded", opening ? "true" : "false");

            if (chevron) {
                chevron.classList.toggle("bi-chevron-down", !opening);
                chevron.classList.toggle("bi-chevron-up", opening);
            }
        });
    });
})();
