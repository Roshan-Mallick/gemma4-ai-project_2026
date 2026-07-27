(function () {
  var WAKEUP_BANNER_ID = "wakeup-banner";
  var POLL_INTERVAL_MS = 4000;
  var MAX_ATTEMPTS = 30;

  function getBackendBase() {
    if (window.location.port === "3000" || window.location.port === "5500" || window.location.port === "8080") {
      return "http://localhost:8000";
    }
    return "";
  }

  function showBanner() {
    if (document.getElementById(WAKEUP_BANNER_ID)) return;
    var banner = document.createElement("div");
    banner.id = WAKEUP_BANNER_ID;
    banner.className = "wakeup-banner";
    banner.innerHTML =
      '<div class="wakeup-banner__inner">' +
        '<span class="wakeup-banner__spinner"></span>' +
        '<span class="wakeup-banner__text">Waking up AI server (first request may take up to 60 seconds)...</span>' +
      "</div>";
    document.body.prepend(banner);
  }

  function hideBanner() {
    var banner = document.getElementById(WAKEUP_BANNER_ID);
    if (banner) {
      banner.classList.add("wakeup-banner--hide");
      setTimeout(function () { banner.remove(); }, 600);
    }
  }

  function ping(attempt) {
    var base = getBackendBase();
    fetch(base + "/health", { method: "GET", cache: "no-store" })
      .then(function (res) {
        if (res.ok) {
          hideBanner();
        } else if (attempt < MAX_ATTEMPTS) {
          setTimeout(function () { ping(attempt + 1); }, POLL_INTERVAL_MS);
        } else {
          hideBanner();
        }
      })
      .catch(function () {
        if (attempt < MAX_ATTEMPTS) {
          setTimeout(function () { ping(attempt + 1); }, POLL_INTERVAL_MS);
        } else {
          hideBanner();
        }
      });
  }

  showBanner();
  setTimeout(function () { ping(0); }, 500);
})();
