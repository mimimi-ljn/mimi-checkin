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
          html += '<div class="ann-item' + (a.active ? '' : ' ann-inactive') + '">';
          html += '<div>';
          html += '<h4>' + escapeHtml(a.title) + (a.active ? '' : ' (已禁用)') + '</h4>';
          html += '<div class="ann-meta">' + pageLabel + ' | ' + time + '</div>';
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
      var title = document.getElementById("ann_title").value.trim();
      var content = document.getElementById("ann_content").value.trim();
      var annPage = document.getElementById("ann_page").value;
      if (!title || !content) { showNotice("请填写标题和内容", "error"); return; }
      try {
        await postJson("/api/v1/admin/announcements", { title: title, content: content, page: annPage, active: true });
        showNotice("公告已发布", "success");
        document.getElementById("ann_title").value = "";
        document.getElementById("ann_content").value = "";
        loadAnnouncements();
      } catch (err) {
        showNotice(err.message || "发布失败", "error");
      }
    });
  }

  function escapeHtml(text) {
    if (!text) return "";
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
})();
