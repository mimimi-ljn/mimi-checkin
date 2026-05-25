(function() {
  var form = document.getElementById("forgotForm");
  var submitBtn = document.getElementById("submitBtn");
  var sendCodeBtn = document.getElementById("sendCodeBtn");
  var msgEl = document.getElementById("message");
  var codeCountdown = 0;

  if (sendCodeBtn) {
    sendCodeBtn.addEventListener("click", async function() {
      if (codeCountdown > 0) return;
      var email = document.getElementById("email").value.trim();
      var username = document.getElementById("username").value.trim();
      if (!email || !username) {
        showNotice("请先输入校园网账号和邮箱", "error");
        return;
      }
      sendCodeBtn.disabled = true;
      try {
        await postJson("/api/v1/auth/send-code", { email: email, purpose: "reset_password" });
        showNotice("验证码已发送", "success");
        codeCountdown = 60;
        updateCountdown();
      } catch (error) {
        showNotice(error.message || "发送失败", "error");
        sendCodeBtn.disabled = false;
      }
    });
  }

  function updateCountdown() {
    if (codeCountdown <= 0) {
      sendCodeBtn.disabled = false;
      sendCodeBtn.textContent = "发送验证码";
      return;
    }
    sendCodeBtn.textContent = codeCountdown + "s 后重发";
    codeCountdown -= 1;
    setTimeout(updateCountdown, 1000);
  }

  if (!form) return;

  form.addEventListener("submit", async function(e) {
    e.preventDefault();

    var username = document.getElementById("username").value.trim();
    var email = document.getElementById("email").value.trim();
    var code = document.getElementById("email_code").value.trim();
    var password = document.getElementById("campus_password").value;

    if (!username || !email || !code || !password) {
      showNotice("请填写所有字段", "error");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "处理中...";

    try {
      await postJson("/api/v1/auth/reset-password", {
        username: username,
        email: email,
        email_code: code,
        campus_password: password
      });
      showNotice("密码重置成功，请登录", "success");
      setTimeout(function() { window.location.href = "/login"; }, 1500);
    } catch (error) {
      showNotice(error.message || "重置失败", "error");
      submitBtn.disabled = false;
      submitBtn.textContent = "重置密码";
    }
  });
})();
