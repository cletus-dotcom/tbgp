(function () {
    "use strict";

    var config = window.TBGP_BGM || {};
    var src = config.src;
    if (!src) {
        return;
    }

    var DEFAULT_VOLUME = 0.1;
    var VOLUME_STEP = 0.05;
    var VOLUME_MAX = 0.4;
    var STORAGE = {
        playing: "tbgp_bgm_playing",
        time: "tbgp_bgm_time",
        ended: "tbgp_bgm_ended",
        unlocked: "tbgp_bgm_unlocked",
        volume: "tbgp_bgm_volume",
        muted: "tbgp_bgm_muted",
    };

    var isHome = Boolean(config.isHome);
    var audio = null;
    var unlockBound = false;
    var taskbar = null;
    var muteBtn = null;
    var volSlider = null;
    var volDownBtn = null;
    var volUpBtn = null;
    var statusEl = null;
    var volumeBeforeMute = DEFAULT_VOLUME;
    var controlsReady = false;

    function clampVolume(value) {
        var num = Number(value);
        if (!Number.isFinite(num)) {
            return DEFAULT_VOLUME;
        }
        return Math.min(VOLUME_MAX, Math.max(0, num));
    }

    function readStoredVolume() {
        var stored = sessionStorage.getItem(STORAGE.volume);
        if (stored === null || stored === "") {
            return DEFAULT_VOLUME;
        }
        return clampVolume(parseFloat(stored));
    }

    function isMuted() {
        return sessionStorage.getItem(STORAGE.muted) === "1";
    }

    function getEffectiveVolume() {
        if (isMuted()) {
            return 0;
        }
        return readStoredVolume();
    }

    function saveVolumeSetting(value) {
        var clamped = clampVolume(value);
        sessionStorage.setItem(STORAGE.volume, String(clamped));
        return clamped;
    }

    function setMuted(muted) {
        if (muted) {
            if (!isMuted()) {
                volumeBeforeMute = readStoredVolume() || DEFAULT_VOLUME;
            }
            sessionStorage.setItem(STORAGE.muted, "1");
        } else {
            sessionStorage.removeItem(STORAGE.muted);
        }
        applyVolume();
        updateTaskbarUI();
    }

    function applyVolume() {
        var level = getEffectiveVolume();
        if (audio) {
            audio.volume = level;
        }
        if (volSlider) {
            volSlider.value = String(Math.round((isMuted() ? volumeBeforeMute : readStoredVolume()) * 100));
        }
    }

    function volumeToPercent(value) {
        return Math.round(clampVolume(value) * 100);
    }

    function percentToVolume(percent) {
        return clampVolume(percent / 100);
    }

    function adjustVolume(delta) {
        if (isMuted()) {
            setMuted(false);
        }
        var next = saveVolumeSetting(readStoredVolume() + delta);
        applyVolume();
        updateTaskbarUI();
        return next;
    }

    function readTime() {
        var value = parseFloat(sessionStorage.getItem(STORAGE.time) || "0");
        return Number.isFinite(value) && value > 0 ? value : 0;
    }

    function isPlayingSession() {
        return sessionStorage.getItem(STORAGE.playing) === "1"
            && sessionStorage.getItem(STORAGE.ended) !== "1";
    }

    function shouldStartFreshOnHome() {
        if (!isHome) {
            return false;
        }
        if (sessionStorage.getItem(STORAGE.ended) === "1") {
            return true;
        }
        return sessionStorage.getItem(STORAGE.playing) !== "1";
    }

    function shouldResume() {
        return isPlayingSession();
    }

    function persistProgress() {
        if (!audio || audio.ended) {
            return;
        }
        sessionStorage.setItem(STORAGE.playing, "1");
        sessionStorage.setItem(STORAGE.time, String(audio.currentTime));
        sessionStorage.removeItem(STORAGE.ended);
    }

    function markEnded() {
        sessionStorage.setItem(STORAGE.ended, "1");
        sessionStorage.removeItem(STORAGE.playing);
        sessionStorage.removeItem(STORAGE.time);
        hideTaskbarEnded();
    }

    function showTaskbar() {
        if (!taskbar) {
            return;
        }
        taskbar.hidden = false;
        taskbar.classList.remove("is-ended");
        document.body.classList.add("bgm-taskbar-active");
        updateTaskbarUI();
    }

    function hideTaskbarEnded() {
        if (!taskbar) {
            return;
        }
        taskbar.classList.add("is-ended");
        if (statusEl) {
            statusEl.textContent = "Finished";
        }
        window.setTimeout(function () {
            if (taskbar) {
                taskbar.hidden = true;
            }
            document.body.classList.remove("bgm-taskbar-active");
        }, 2500);
    }

    function updateTaskbarUI() {
        if (!controlsReady) {
            return;
        }
        var muted = isMuted();
        var level = readStoredVolume();
        if (volSlider) {
            volSlider.value = String(volumeToPercent(muted ? volumeBeforeMute : level));
        }
        if (muteBtn) {
            var icon = muteBtn.querySelector("i");
            muteBtn.classList.toggle("is-muted", muted);
            muteBtn.setAttribute("aria-label", muted ? "Unmute background music" : "Mute background music");
            muteBtn.title = muted ? "Unmute" : "Mute";
            if (icon) {
                icon.className = muted ? "bi bi-volume-mute-fill" : (level < 0.08 ? "bi bi-volume-down-fill" : "bi bi-volume-up-fill");
            }
        }
        if (statusEl && !taskbar.classList.contains("is-ended")) {
            statusEl.textContent = muted ? "Muted" : (volumeToPercent(level) + "%");
        }
    }

    function bindTaskbarControls() {
        taskbar = document.getElementById("bgmTaskbar");
        muteBtn = document.getElementById("bgmMuteBtn");
        volSlider = document.getElementById("bgmVolSlider");
        volDownBtn = document.getElementById("bgmVolDown");
        volUpBtn = document.getElementById("bgmVolUp");
        statusEl = document.getElementById("bgmTaskbarStatus");

        if (!taskbar || !muteBtn || !volSlider) {
            return;
        }

        volumeBeforeMute = readStoredVolume();
        applyVolume();
        controlsReady = true;

        muteBtn.addEventListener("click", function () {
            setMuted(!isMuted());
        });

        volDownBtn?.addEventListener("click", function () {
            adjustVolume(-VOLUME_STEP);
        });

        volUpBtn?.addEventListener("click", function () {
            adjustVolume(VOLUME_STEP);
        });

        volSlider.addEventListener("input", function () {
            if (isMuted()) {
                setMuted(false);
            }
            saveVolumeSetting(percentToVolume(parseInt(volSlider.value, 10)));
            applyVolume();
            updateTaskbarUI();
        });
    }

    function createAudio() {
        if (audio) {
            return audio;
        }
        audio = new Audio(src);
        audio.volume = getEffectiveVolume();
        audio.loop = false;
        audio.preload = "auto";

        audio.addEventListener("ended", function () {
            markEnded();
            audio = null;
        });

        audio.addEventListener("timeupdate", function () {
            if (!audio.paused) {
                persistProgress();
            }
        });

        audio.addEventListener("play", function () {
            showTaskbar();
        });

        return audio;
    }

    function bindUnlockOnce(player) {
        if (unlockBound || sessionStorage.getItem(STORAGE.unlocked) === "1") {
            return;
        }
        unlockBound = true;

        function unlock() {
            sessionStorage.setItem(STORAGE.unlocked, "1");
            document.removeEventListener("click", unlock);
            document.removeEventListener("keydown", unlock);
            document.removeEventListener("touchstart", unlock);
            if (player.paused && !player.ended) {
                player.play().catch(function () {});
            }
        }

        document.addEventListener("click", unlock, { once: true, passive: true });
        document.addEventListener("keydown", unlock, { once: true });
        document.addEventListener("touchstart", unlock, { once: true, passive: true });
    }

    function playFrom(startAt) {
        var player = createAudio();
        player.volume = getEffectiveVolume();
        player.currentTime = startAt;
        sessionStorage.setItem(STORAGE.playing, "1");
        sessionStorage.removeItem(STORAGE.ended);
        showTaskbar();

        var attempt = player.play();
        if (attempt && typeof attempt.catch === "function") {
            attempt.catch(function () {
                bindUnlockOnce(player);
            });
        }
        bindUnlockOnce(player);
        updateTaskbarUI();
    }

    function beginPlayback() {
        if (shouldResume()) {
            playFrom(readTime());
            return;
        }
        if (shouldStartFreshOnHome()) {
            sessionStorage.removeItem(STORAGE.ended);
            playFrom(0);
        }
    }

    function waitForHomeLoader(callback) {
        var loader = document.getElementById("nationLoader");
        if (!loader) {
            callback();
            return;
        }

        function runWhenReady() {
            if (loader.classList.contains("done")) {
                callback();
                return true;
            }
            return false;
        }

        if (runWhenReady()) {
            return;
        }

        var observer = new MutationObserver(function () {
            if (runWhenReady()) {
                observer.disconnect();
            }
        });
        observer.observe(loader, { attributes: true, attributeFilter: ["class"] });
        window.setTimeout(function () {
            observer.disconnect();
            callback();
        }, 5200);
    }

    function init() {
        bindTaskbarControls();

        if (shouldResume()) {
            showTaskbar();
            beginPlayback();
            return;
        }
        if (shouldStartFreshOnHome()) {
            waitForHomeLoader(beginPlayback);
        }
    }

    window.TBGP_BGM_save = persistProgress;
    window.TBGP_BGM = Object.assign({}, config, {
        setVolume: function (value) {
            if (isMuted()) {
                setMuted(false);
            }
            saveVolumeSetting(value);
            applyVolume();
            updateTaskbarUI();
        },
        setMuted: setMuted,
        getVolume: readStoredVolume,
        isMuted: isMuted,
    });

    window.addEventListener("pagehide", persistProgress);
    window.addEventListener("beforeunload", persistProgress);

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
