(function () {
    const screensaver = document.getElementById("idleScreensaver");
    if (!screensaver) return;

    const resumeBtn = document.getElementById("idleScreensaverResume");
    const idleTime = Number(screensaver.dataset.idleTime || 120000);
    const activityEvents = ["mousemove", "mousedown", "keydown", "touchstart", "scroll"];
    let idleTimer = null;
    let isActive = false;

    function showScreensaver() {
        isActive = true;
        screensaver.classList.add("active");
        screensaver.setAttribute("aria-hidden", "false");
    }

    function hideScreensaver() {
        if (!isActive) return;
        isActive = false;
        screensaver.classList.remove("active");
        screensaver.setAttribute("aria-hidden", "true");
    }

    function resetIdleTimer() {
        window.clearTimeout(idleTimer);
        hideScreensaver();
        idleTimer = window.setTimeout(showScreensaver, idleTime);
    }

    activityEvents.forEach((eventName) => {
        document.addEventListener(eventName, resetIdleTimer, { passive: true });
    });

    screensaver.addEventListener("click", hideScreensaver);
    resumeBtn?.addEventListener("click", hideScreensaver);
    resetIdleTimer();
})();
