async function fetchJson(url, options) {
  if (!options) options = {};
  options.credentials = "same-origin";
  const response = await fetch(url, options);
  const data = response.status === 204 ? null : await response.json().catch(function() { return null; });
  if (!response.ok) {
    var message = data?.detail || data?.message || (response.status === 401 ? "登录已过期，请重新登录" : "请求失败");
    if (Array.isArray(message)) {
      message = message.map(function(item) { return item?.msg || item?.message || "参数有误"; }).join("；");
    } else if (message && typeof message === "object") {
      message = message.msg || message.message || "请求参数有误";
    }
    var error = new Error(message);
    error.status = response.status;
    error.retryAfter = Number(response.headers.get("Retry-After") || 0);

    var path = window.location.pathname;
    var isAuthRequest = typeof url === "string" && url.startsWith("/api/v1/auth/");
    var isAuthPage = ["/login", "/register", "/forgot-password"].some(function(p) { return path.startsWith(p); });
    if (response.status === 401 && !isAuthRequest && !isAuthPage) {
      setTimeout(function() {
        window.location.href = "/login?next=" + encodeURIComponent(path);
      }, 900);
    }
    throw error;
  }
  return data;
}

async function postJson(url, payload, method) {
  if (!method) method = "POST";
  var options = { method: method };
  if (payload !== undefined) {
    options.headers = {"Content-Type": "application/json"};
    options.body = JSON.stringify(payload);
  }
  return fetchJson(url, options);
}

var noticeDedupState = new Map();

function noticeDedupKey(message, type) {
  return (type || "success") + ":" + String(message || "").trim();
}

function showNotice(message, type, options) {
  if (!message) return null;
  type = type || "success";
  options = options || {};
  var duration = Number(options.duration || 5200);
  var dedupWindow = Number(options.dedupWindow || 1400);
  var dedupKey = noticeDedupKey(message, type);
  var now = Date.now();
  var existing = noticeDedupState.get(dedupKey);
  if (existing?.notice?.isConnected && !existing.notice.classList.contains("notice-toast-hide")) {
    existing.notice.classList.remove("notice-toast-pulse");
    void existing.notice.offsetWidth;
    existing.notice.classList.add("notice-toast-pulse");
    return existing.notice;
  }
  if (existing?.closedAt && now - existing.closedAt < dedupWindow) {
    return null;
  }

  var host = document.body;
  var stack = document.querySelector(".notice-stack");
  if (!stack) {
    stack = document.createElement("div");
    stack.className = "notice-stack";
    host.appendChild(stack);
  }

  var notice = document.createElement("div");
  notice.className = "notice-toast notice-toast-" + (type === "success" ? "success" : "error");
  notice.setAttribute("role", type === "success" ? "status" : "alert");
  notice.textContent = message;
  stack.appendChild(notice);
  noticeDedupState.set(dedupKey, {notice: notice, closedAt: 0});

  var close = function() {
    if (notice.classList.contains("notice-toast-hide")) return;
    notice.classList.add("notice-toast-hide");
    var state = noticeDedupState.get(dedupKey);
    if (state?.notice === notice) {
      noticeDedupState.set(dedupKey, {notice: null, closedAt: Date.now()});
      setTimeout(function() {
        var latest = noticeDedupState.get(dedupKey);
        if (latest?.notice === null && Date.now() - latest.closedAt >= dedupWindow) {
          noticeDedupState.delete(dedupKey);
        }
      }, dedupWindow);
    }
    setTimeout(function() { notice.remove(); }, 220);
  };
  setTimeout(close, duration);
  notice.addEventListener("click", close);
  return notice;
}

window.showNotice = showNotice;

// Loading animation
(function() {
  var loading = document.querySelector(".page-loading");
  if (!loading) {
    loading = document.createElement("div");
    loading.className = "page-loading";
    loading.innerHTML = '<div class="loading-spinner-large"></div>';
    document.body.appendChild(loading);
  }
  window.addEventListener("load", function() {
    loading.style.opacity = "0";
    setTimeout(function() { loading.parentNode?.removeChild(loading); }, 500);
  });
})();

// Scroll effect on nav
document.addEventListener("DOMContentLoaded", function() {
  var topNav = document.querySelector(".top-nav");
  window.addEventListener("scroll", function() {
    topNav?.classList.toggle("scrolled", window.scrollY > 50);
  });

  // Logout
  var navLogout = document.getElementById("navLogout");
  if (navLogout) {
    navLogout.addEventListener("click", async function(e) {
      e.preventDefault();
      await postJson("/api/v1/auth/logout", {});
      window.location.href = "/";
    });
  }
});

// Announcements modal
document.addEventListener("DOMContentLoaded", async function() {
  var modal = document.getElementById("announcement-modal");
  var confirmBtn = document.getElementById("confirm-modal");
  var announcementTitle = document.getElementById("announcement-title");
  var announcementContent = document.getElementById("announcement-content");
  var announcementsQueue = [];
  var currentIndex = 0;

  function closeModal() {
    if (!modal) return;
    modal.style.display = "none";
    document.body.classList.remove("modal-open");
  }

  function openModal() {
    setTimeout(function() {
      if (modal && announcementsQueue.length > 0) {
        modal.style.display = "flex";
        document.body.classList.add("modal-open");
      }
    }, 600);
  }

  function render() {
    var current = announcementsQueue[currentIndex];
    if (!current || !announcementTitle || !announcementContent || !confirmBtn) {
      closeModal();
      return;
    }
    var total = announcementsQueue.length;
    announcementTitle.textContent = total > 1
      ? "系统公告 (" + (currentIndex + 1) + "/" + total + "): " + current.title
      : current.title;
    announcementContent.textContent = current.content;
    announcementContent.style.whiteSpace = "pre-line";
    confirmBtn.textContent = currentIndex < total - 1 ? "下一条" : "已阅";
  }

  if (confirmBtn) {
    confirmBtn.addEventListener("click", function() {
      if (currentIndex < announcementsQueue.length - 1) {
        currentIndex += 1;
        render();
        return;
      }
      closeModal();
    });
  }

  var currentPage = document.body.dataset.page || "home";
  if (["terms", "forgot-password"].indexOf(currentPage) !== -1) return;

  try {
    var data = await fetchJson("/api/v1/announcements?page=" + currentPage);
    announcementsQueue = data.filter(function(item) { return item && item.title && item.content; });
    currentIndex = 0;
    if (announcementsQueue.length > 0) {
      render();
      openModal();
    }
  } catch (e) {
    console.error("获取公告失败:", e);
  }
});
