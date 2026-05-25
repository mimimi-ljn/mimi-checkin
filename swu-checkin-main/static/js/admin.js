(function() {
  var page = document.body.dataset.page || "admin-overview";

  // ── Overview ──────────────────────────────────────────────────────
  if (page === "admin-overview") {
    loadOverview();
  }

  async function loadOverview() {
    try {
      var data = await fetchJson("/api/v1/admin/overview");
      document.getElementById("statUsers").textContent = data.total_users;
      document.getElementById("statAuto").textContent = data.auto_users;
      document.getElementById("statTotal").textContent = data.total_checkins;
      document.getElementById("statToday").textContent = data.today_checkins;

      var html = "";
      if (data.recent_logs.length === 0) {
        html = '<p class="muted">暂无记录</p>';
      } else {
        data.recent_logs.forEach(function(log) {
          var cls = "status-" + (log.status || "");
          var time = log.created_at ? new Date(log.created_at).toLocaleString("zh-CN") : "";
          html += '<div class="log-item">';
          html += '<span class="log-status ' + cls + '">' + escapeHtml(log.username) + '</span>';
          html += '<span class="log-msg">' + escapeHtml(log.message || log.status) + '</span>';
          html += '<span class="log-time">' + time + '</span>';
          html += "</div>";
        });
      }
      document.getElementById("recentLogs").innerHTML = html;
    } catch (e) {
      document.getElementById("recentLogs").innerHTML = '<p class="muted">加载失败</p>';
    }
  }

  // ── Settings ──────────────────────────────────────────────────────
  if (page === "admin-settings") {
    loadSettings();
  }

  async function loadSettings() {
    try {
      var data = await fetchJson("/api/v1/admin/settings");
      var map = {};
      data.settings.forEach(function(s) { map[s.key] = s.value; });

      setVal("set_site_title", map.site_title || "签到系统");
      setVal("set_home_notice", map.home_notice || "");
      setCheck("set_registration_enabled", map.registration_enabled !== "false");
      setCheck("set_payment_enabled", map.payment_enabled !== "false");
      setCheck("set_manual_checkin_enabled", map.manual_checkin_enabled !== "false");
      setVal("set_new_user_credits", map.new_user_credits || "3");
      setVal("set_package_price", map.package_price || "3");
      setVal("set_package_count", map.package_count || "30");
      setVal("set_pricing_text", map.pricing_text || "3 元 / 30 次");
    } catch (e) {
      showNotice("加载设置失败", "error");
    }
  }

  function setVal(id, value) {
    var el = document.getElementById(id);
    if (el) {
      if (el.type === "textarea") el.value = value;
      else el.value = value;
    }
  }

  function setCheck(id, checked) {
    var el = document.getElementById(id);
    if (el) el.checked = checked;
  }

  var settingsForm = document.getElementById("settingsForm");
  if (settingsForm) {
    settingsForm.addEventListener("submit", async function(e) {
      e.preventDefault();
      var settings = {
        site_title: document.getElementById("set_site_title").value,
        home_notice: document.getElementById("set_home_notice").value,
        registration_enabled: document.getElementById("set_registration_enabled").checked ? "true" : "false",
        payment_enabled: document.getElementById("set_payment_enabled").checked ? "true" : "false",
        manual_checkin_enabled: document.getElementById("set_manual_checkin_enabled").checked ? "true" : "false",
        new_user_credits: document.getElementById("set_new_user_credits").value,
        package_price: document.getElementById("set_package_price").value,
        package_count: document.getElementById("set_package_count").value,
        pricing_text: document.getElementById("set_pricing_text").value,
      };
      try {
        await postJson("/api/v1/admin/settings", { settings: settings }, "PUT");
        showNotice("设置已保存", "success");
      } catch (err) {
        showNotice(err.message || "保存失败", "error");
      }
    });
  }

  // ── Announcements ─────────────────────────────────────────────────
  if (page === "admin-announcements") {
    loadAnnouncements();
    loadUserOptions();
  }

  var _userMap = {}; // id → username for announcement display

  async function loadUserOptions() {
    try {
      var users = await fetchJson("/api/v1/admin/users/simple");
      var sel = document.getElementById("ann_target_user");
      if (!sel) return;
      users.forEach(function(u) {
        _userMap[u.id] = u.username;
        var opt = document.createElement("option");
        opt.value = u.id;
        opt.textContent = u.username + " (ID:" + u.id + ")";
        sel.appendChild(opt);
      });
    } catch (e) {
      // dropdown stays with just "所有人" option
    }
  }

  async function loadAnnouncements() {
    try {
      var data = await fetchJson("/api/v1/admin/announcements");
      var html = "";
      if (data.items.length === 0) {
        html = '<p class="muted">暂无公告</p>';
      } else {
        data.items.forEach(function(a) {
          var time = a.created_at ? new Date(a.created_at).toLocaleString("zh-CN") : "";
          var pageLabel = { all: "所有页面", home: "首页", login: "登录", register: "注册", dashboard: "仪表盘" }[a.page] || a.page;
          var targetLabel = a.target_user_id ? ("用户：" + (getUsername(a.target_user_id) || "ID:" + a.target_user_id)) : "全局";
          html += '<div class="ann-item' + (a.active ? '' : ' ann-inactive') + '">';
          html += '<div>';
          html += '<h4>' + escapeHtml(a.title) + (a.active ? '' : ' (已禁用)') + '</h4>';
          html += '<div class="ann-meta">' + targetLabel + ' | ' + pageLabel + ' | ' + time + '</div>';
          html += '<div style="margin-top:4px;font-size:13px;color:var(--text-secondary);">' + escapeHtml(a.content.substring(0, 100)) + '</div>';
          html += '</div>';
          html += '<div class="ann-actions">';
          html += '<button class="btn btn-sm btn-soft" onclick="window._toggleAnn(' + a.id + ', ' + !a.active + ')">' + (a.active ? '禁用' : '启用') + '</button>';
          html += '<button class="btn btn-sm btn-danger" onclick="window._deleteAnn(' + a.id + ')">删除</button>';
          html += '</div>';
          html += '</div>';
        });
      }
      document.getElementById("annList").innerHTML = html;
    } catch (e) {
      document.getElementById("annList").innerHTML = '<p class="muted">加载失败</p>';
    }
  }

  function getUsername(uid) {
    return _userMap[uid] || null;
  }

  window._toggleAnn = async function(id, active) {
    try {
      await postJson("/api/v1/admin/announcements/" + id, { active: active }, "PUT");
      showNotice(active ? "公告已启用" : "公告已禁用", "success");
      loadAnnouncements();
    } catch (e) {
      showNotice(e.message || "操作失败", "error");
    }
  };

  window._deleteAnn = async function(id) {
    if (!confirm("确定删除此公告？")) return;
    try {
      await postJson("/api/v1/admin/announcements/" + id, undefined, "DELETE");
      showNotice("公告已删除", "success");
      loadAnnouncements();
    } catch (e) {
      showNotice(e.message || "删除失败", "error");
    }
  };

  // ── New announcement form ─────────────────────────────────────────
  var newForm = document.getElementById("newAnnounceForm");
  if (newForm) {
    newForm.addEventListener("submit", async function(e) {
      e.preventDefault();
      try {
        var titleEl = document.getElementById("ann_title");
        var contentEl = document.getElementById("ann_content");
        var pageEl = document.getElementById("ann_page");
        var targetEl = document.getElementById("ann_target_user");
        var title = titleEl ? titleEl.value.trim() : "";
        var content = contentEl ? contentEl.value.trim() : "";
        var annPage = pageEl ? pageEl.value : "all";
        var targetUserId = targetEl ? targetEl.value : "";
        if (!title || !content) { showNotice("请填写标题和内容", "error"); return; }
        var payload = { title: title, content: content, page: annPage, active: true };
        if (targetUserId) payload.target_user_id = parseInt(targetUserId, 10);
        await postJson("/api/v1/admin/announcements", payload);
        showNotice("公告已发布", "success");
        if (titleEl) titleEl.value = "";
        if (contentEl) contentEl.value = "";
        if (targetEl) targetEl.value = "";
        loadAnnouncements();
      } catch (err) {
        showNotice(err.message || "发布失败", "error");
      }
    });
  }

  // ── Users ─────────────────────────────────────────────────────────
  if (page === "admin-users") {
    loadUsers();
  }

  var currentUserPage = 1;
  var currentUserSearch = "";
  var _userCache = {}; // store user info for safe onclick access

  async function loadUsers(p, search) {
    if (p === undefined) p = currentUserPage;
    if (search === undefined) search = currentUserSearch;
    currentUserPage = p;
    currentUserSearch = search;

    var url = "/api/v1/admin/users?page=" + p + "&per_page=50";
    if (search) url += "&search=" + encodeURIComponent(search);

    try {
      var data = await fetchJson(url);
      _userCache = {};
      var html = "";
      if (data.items.length === 0) {
        html = '<tr><td colspan="9" class="muted" style="text-align:center;padding:24px;">暂无用户</td></tr>';
      } else {
        data.items.forEach(function(u) {
          _userCache[u.id] = { username: u.username, credits: u.credits };
          var autoLabel = u.auto_checkin ? "是" : "否";
          var lastCheckin = u.last_checkin ? new Date(u.last_checkin).toLocaleString("zh-CN") : "-";
          var createdAt = u.created_at ? new Date(u.created_at).toLocaleString("zh-CN") : "-";
          html += '<tr>';
          html += '<td>' + u.id + '</td>';
          html += '<td><strong>' + escapeHtml(u.username) + '</strong></td>';
          html += '<td>' + escapeHtml(u.email) + '</td>';
          html += '<td><span class="credits-value">' + u.credits + '</span></td>';
          html += '<td>' + autoLabel + '</td>';
          html += '<td>' + u.login_count + '</td>';
          html += '<td class="time-cell">' + lastCheckin + '</td>';
          html += '<td class="time-cell">' + createdAt + '</td>';
          html += '<td class="action-cell">';
          html += '<button class="btn btn-sm btn-soft" onclick="window._openCreditModal(' + u.id + ')">调整次数</button>';
          html += '</td>';
          html += '</tr>';
        });
      }
      document.getElementById("userTableBody").innerHTML = html;
      renderUserPagination(data);
    } catch (e) {
      document.getElementById("userTableBody").innerHTML = '<tr><td colspan="9" class="muted" style="text-align:center;padding:24px;">加载失败</td></tr>';
    }
  }

  function renderUserPagination(data) {
    var el = document.getElementById("userPagination");
    if (!el) return;
    if (data.pages <= 1) { el.innerHTML = ""; return; }
    var html = '<div class="log-pagination">';
    html += '<button class="btn btn-sm btn-soft"' + (data.page <= 1 ? ' disabled' : '') + ' onclick="window._goUserPage(' + (data.page - 1) + ')">上一页</button>';
    html += '<span style="padding:6px 12px;font-size:13px;color:var(--text-secondary);">第 ' + data.page + ' / ' + data.pages + ' 页（共 ' + data.total + ' 人）</span>';
    html += '<button class="btn btn-sm btn-soft"' + (data.page >= data.pages ? ' disabled' : '') + ' onclick="window._goUserPage(' + (data.page + 1) + ')">下一页</button>';
    html += '</div>';
    el.innerHTML = html;
  }

  window._goUserPage = function(p) {
    loadUsers(p);
  };

  var userSearchInput = document.getElementById("userSearch");
  var userSearchBtn = document.getElementById("userSearchBtn");
  if (userSearchBtn && userSearchInput) {
    userSearchBtn.addEventListener("click", function() {
      loadUsers(1, userSearchInput.value.trim());
    });
    userSearchInput.addEventListener("keydown", function(e) {
      if (e.key === "Enter") loadUsers(1, userSearchInput.value.trim());
    });
  }

  // ── Credit adjustment modal ─────────────────────────────────────────
  var creditModal = document.getElementById("creditModal");
  var creditModalUser = document.getElementById("creditModalUser");
  var creditDelta = document.getElementById("creditDelta");
  var creditModalMsg = document.getElementById("creditModalMsg");
  var creditModalCancel = document.getElementById("creditModalCancel");
  var creditModalConfirm = document.getElementById("creditModalConfirm");
  var currentEditUserId = null;

  window._openCreditModal = function(id) {
    var info = _userCache[id] || { username: "未知", credits: 0 };
    currentEditUserId = id;
    creditModalUser.textContent = "用户：" + info.username + "（当前次数：" + info.credits + "）";
    creditDelta.value = "";
    if (creditModalMsg) creditModalMsg.classList.remove("show", "success");
    creditModal.style.display = "flex";
    document.body.classList.add("modal-open");
    creditDelta.focus();
  };

  if (creditModalCancel && creditModal) {
    creditModalCancel.addEventListener("click", function() {
      creditModal.style.display = "none";
      document.body.classList.remove("modal-open");
      currentEditUserId = null;
    });
    creditModal.addEventListener("click", function(e) {
      if (e.target === creditModal) {
        creditModal.style.display = "none";
        document.body.classList.remove("modal-open");
        currentEditUserId = null;
      }
    });
  }

  if (creditModalConfirm) {
    creditModalConfirm.addEventListener("click", async function() {
      if (!currentEditUserId) return;
      var delta = parseInt(creditDelta.value, 10);
      if (isNaN(delta) || delta === 0) {
        if (creditModalMsg) { creditModalMsg.textContent = "请输入有效的非零整数"; creditModalMsg.classList.add("show"); creditModalMsg.classList.remove("success"); }
        return;
      }
      creditModalConfirm.disabled = true;
      try {
        var result = await postJson("/api/v1/admin/users/" + currentEditUserId + "/credits", { delta: delta }, "PUT");
        if (creditModalMsg) { creditModalMsg.textContent = result.message; creditModalMsg.classList.add("show", "success"); }
        loadUsers(); // refresh list
        setTimeout(function() {
          creditModal.style.display = "none";
          document.body.classList.remove("modal-open");
          currentEditUserId = null;
        }, 800);
      } catch (e) {
        if (creditModalMsg) { creditModalMsg.textContent = e.message || "操作失败"; creditModalMsg.classList.add("show"); creditModalMsg.classList.remove("success"); }
      }
      creditModalConfirm.disabled = false;
    });
  }

  function escapeHtml(text) {
    if (!text) return "";
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
})();
