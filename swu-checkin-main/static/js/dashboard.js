(function() {
  var manualBtn = document.getElementById("manualCheckinBtn");
  var buyBtn = document.getElementById("buyCreditsBtn");
  var toggleAutoBtn = document.getElementById("toggleAutoBtn");
  var logPage = 1;

  // Load all dashboard data
  async function loadDashboard() {
    try {
      var status = await fetchJson("/api/v1/checkin/status");
      renderStatus(status);
    } catch (e) {
      if (e.status === 401) return;
      document.getElementById("todayStatus").textContent = "加载失败";
    }

    loadLogs(1);
    loadOrders();
  }

  function renderStatus(status) {
    var todayMap = {
      "pending": "等待签到",
      "success": "已签到",
      "already_done": "今日已签到"
    };
    document.getElementById("todayStatus").textContent = todayMap[status.today_status] || status.today_status || "等待签到";
    document.getElementById("todayHint").textContent = status.today_message || "";
    document.getElementById("credits").textContent = status.credits;
    document.getElementById("autoStatus").textContent = status.auto_checkin ? "已开启" : "已关闭";

    if (toggleAutoBtn) {
      toggleAutoBtn.setAttribute("data-enabled", status.auto_checkin ? "true" : "false");
      toggleAutoBtn.textContent = status.auto_checkin ? "关闭自动" : "开启自动";
      if (status.auto_checkin) {
        toggleAutoBtn.classList.add("btn-secondary");
        toggleAutoBtn.classList.remove("btn-soft");
      } else {
        toggleAutoBtn.classList.remove("btn-secondary");
        toggleAutoBtn.classList.add("btn-soft");
      }
    }

    // Highlight today status
    var todayEl = document.getElementById("todayStatus");
    if (status.today_status === "success" || status.today_status === "already_done") {
      todayEl.style.color = "var(--success)";
    } else {
      todayEl.style.color = "var(--text-primary)";
    }
  }

  // Manual check-in
  if (manualBtn) {
    manualBtn.addEventListener("click", async function() {
      manualBtn.disabled = true;
      manualBtn.textContent = "签到中...";
      try {
        var result = await postJson("/api/v1/checkin/manual", {});
        showNotice(result.message, result.status === "success" ? "success" : "error");
        loadDashboard();
      } catch (error) {
        showNotice(error.message || "签到失败", "error");
      }
      manualBtn.disabled = false;
      manualBtn.textContent = "手动签到";
    });
  }

  // Toggle auto check-in
  if (toggleAutoBtn) {
    toggleAutoBtn.addEventListener("click", async function() {
      var current = toggleAutoBtn.getAttribute("data-enabled") === "true";
      toggleAutoBtn.disabled = true;
      try {
        var result = await postJson("/api/v1/checkin/auto", { enable: !current });
        showNotice(result.message, "success");
        loadDashboard();
      } catch (error) {
        showNotice(error.message || "操作失败", "error");
      }
      toggleAutoBtn.disabled = false;
    });
  }

  // Buy credits
  if (buyBtn) {
    buyBtn.addEventListener("click", async function() {
      buyBtn.disabled = true;
      buyBtn.textContent = "创建订单中...";
      try {
        var order = await postJson("/api/v1/orders", {});
        // Simulate payment
        var paid = await postJson("/api/v1/orders/" + order.id + "/pay", {});
        showNotice("支付成功！已增加 " + paid.credits_added + " 次签到次数", "success");
        loadDashboard();
        loadOrders();
      } catch (error) {
        showNotice(error.message || "购买失败", "error");
      }
      buyBtn.disabled = false;
      buyBtn.textContent = "购买次数 (3元/30次)";
    });
  }

  // Load logs
  async function loadLogs(page) {
    logPage = page;
    var logList = document.getElementById("logList");
    if (!logList) return;
    try {
      var data = await fetchJson("/api/v1/checkin/logs?page=" + page + "&per_page=10");
      if (!data.items || data.items.length === 0) {
        logList.innerHTML = '<p class="muted">暂无签到记录</p>';
        document.getElementById("logPagination").innerHTML = "";
        return;
      }
      var html = "";
      data.items.forEach(function(log) {
        var cls = "status-" + (log.status || "");
        var time = log.created_at ? new Date(log.created_at).toLocaleString("zh-CN") : "";
        html += '<div class="log-item">';
        html += '<span class="log-status ' + cls + '">' + escapeHtml(log.status || "") + '</span>';
        html += '<span class="log-msg">' + escapeHtml(log.message || "") + '</span>';
        html += '<span class="log-time">' + time + '</span>';
        html += "</div>";
      });
      logList.innerHTML = html;

      // Pagination
      var pagesHtml = "";
      for (var i = 1; i <= data.pages; i++) {
        pagesHtml += '<button class="btn btn-sm ' + (i === page ? "btn-primary" : "btn-soft") + '" onclick="window._goLogPage(' + i + ')">' + i + '</button>';
      }
      document.getElementById("logPagination").innerHTML = pagesHtml;
    } catch (e) {
      logList.innerHTML = '<p class="muted">加载日志失败</p>';
    }
  }

  window._goLogPage = function(page) { loadLogs(page); };

  // Load orders
  async function loadOrders() {
    var orderList = document.getElementById("orderList");
    if (!orderList) return;
    try {
      var data = await fetchJson("/api/v1/orders");
      if (!data.items || data.items.length === 0) {
        orderList.innerHTML = '<p class="muted">暂无记录</p>';
        return;
      }
      var html = "";
      data.items.forEach(function(o) {
        var time = o.created_at ? new Date(o.created_at).toLocaleString("zh-CN") : "";
        var statusText = o.status === "paid" ? "已支付" : "待支付";
        html += '<div class="order-item">';
        html += '<span>' + o.order_no + '</span>';
        html += '<span>' + o.credits + ' 次 / ' + o.amount + ' 元</span>';
        html += '<span class="order-status status-' + o.status + '">' + statusText + '</span>';
        html += '<span style="font-size:12px;color:var(--text-muted)">' + time + '</span>';
        if (o.status === "pending") {
          html += '<button class="btn btn-sm btn-soft" onclick="window._deleteOrder(' + o.id + ')">删除</button>';
        }
        html += "</div>";
      });
      orderList.innerHTML = html;
    } catch (e) {
      orderList.innerHTML = '<p class="muted">加载失败</p>';
    }
  }

  window._deleteOrder = async function(id) {
    try {
      await postJson("/api/v1/orders/" + id, undefined, "DELETE");
      showNotice("订单已删除", "success");
      loadOrders();
    } catch (e) {
      showNotice(e.message || "删除失败", "error");
    }
  };

  // Settings form
  var settingsForm = document.getElementById("settingsForm");
  if (settingsForm) {
    settingsForm.addEventListener("submit", async function(e) {
      e.preventDefault();
      var password = document.getElementById("settingsPassword").value;
      var email = document.getElementById("settingsEmail").value.trim();
      var payload = {};
      if (password) payload.campus_password = password;
      if (email) payload.email = email;
      if (Object.keys(payload).length === 0) {
        showNotice("没有需要修改的内容", "error");
        return;
      }
      try {
        await postJson("/api/v1/users/me", payload, "PUT");
        showNotice("设置已更新", "success");
        document.getElementById("settingsPassword").value = "";
        document.getElementById("settingsEmail").value = "";
      } catch (error) {
        showNotice(error.message || "更新失败", "error");
      }
    });
  }

  // Delete account
  var sendDeleteCodeBtn = document.getElementById("sendDeleteCodeBtn");
  var deleteCountdown = 0;

  if (sendDeleteCodeBtn) {
    sendDeleteCodeBtn.addEventListener("click", async function() {
      if (deleteCountdown > 0) return;
      sendDeleteCodeBtn.disabled = true;
      try {
        await postJson("/api/v1/auth/send-code", { email: "", purpose: "delete" });
        showNotice("验证码已发送到注册邮箱", "success");
        deleteCountdown = 60;
        updateDeleteCountdown();
      } catch (error) {
        showNotice(error.message || "发送失败", "error");
        sendDeleteCodeBtn.disabled = false;
      }
    });
  }

  function updateDeleteCountdown() {
    if (deleteCountdown <= 0) {
      sendDeleteCodeBtn.disabled = false;
      sendDeleteCodeBtn.textContent = "发送验证码";
      return;
    }
    sendDeleteCodeBtn.textContent = deleteCountdown + "s 后重发";
    deleteCountdown -= 1;
    setTimeout(updateDeleteCountdown, 1000);
  }

  var deleteBtn = document.getElementById("deleteAccountBtn");
  if (deleteBtn) {
    deleteBtn.addEventListener("click", async function() {
      var code = document.getElementById("deleteEmailCode").value.trim();
      if (!code) {
        showNotice("请输入邮箱验证码", "error");
        return;
      }
      if (!confirm("确定要删除账号吗？此操作不可撤销。")) return;
      deleteBtn.disabled = true;
      try {
        await postJson("/api/v1/users/me", { email_code: code }, "DELETE");
        window.location.href = "/";
      } catch (error) {
        showNotice(error.message || "删除失败", "error");
        deleteBtn.disabled = false;
      }
    });
  }

  function escapeHtml(text) {
    if (!text) return "";
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // Initial load
  loadDashboard();
})();
