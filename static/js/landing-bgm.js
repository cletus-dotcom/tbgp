(function () {
    "use strict";

    var config = window.TBGP_BGM || {};
    var src = config.src;
    if (!src) {
        return;
    }

    var VOLUME = 0.22;
    var STORAGE = {
        playing: "tbgp_bgm_playing",
        time: "tbgp_bgm_time",
        ended: "tbgp_bgm_ended",
        unlocked: "tbgp_bgm_unlocked",
    };

    var isHome = Boolean(config.isHome);
    var audio = null;
    var unlockBound = false;

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

    window.TBGP_BGM_save = persistProgress;

    function markEnded() {
        sessionStorage.setItem(STORAGE.ended, "1");
        sessionStorage.removeItem(STORAGE.playing);
        sessionStorage.removeItem(STORAGE.time);
    }

    function createAudio() {
        if (audio) {
            return audio;
        }
        audio = new Audio(src);
        audio.volume = VOLUME;
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
        player.currentTime = startAt;
        sessionStorage.setItem(STORAGE.playing, "1");
        sessionStorage.removeItem(STORAGE.ended);

        var attempt = player.play();
        if (attempt && typeof attempt.catch === "function") {
            attempt.catch(function () {
                bindUnlockOnce(player);
            });
        }
        bindUnlockOnce(player);
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
        setTimeout(function () {
            observer.disconnect();
            callback();
        }, 5200);
    }

    function init() {
        if (shouldResume()) {
            beginPlayback();
            return;
        }
        if (shouldStartFreshOnHome()) {
            waitForHomeLoader(beginPlayback);
        }
    }

    window.addEventListener("pagehide", persistProgress);
    window.addEventListener("beforeunload", persistProgress);

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
