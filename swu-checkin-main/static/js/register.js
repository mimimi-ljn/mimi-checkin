(function() {
  var form = document.getElementById("registerForm");
  var submitBtn = document.getElementById("submitBtn");
  var sendCodeBtn = document.getElementById("sendCodeBtn");
  var msgEl = document.getElementById("message");
  var termsAccepted = false;
  var codeCountdown = 0;

  // Terms modal
  var termsModal = document.getElementById("registerTermsModal");
  var openTermsBtn = document.getElementById("openTermsModal");
  var confirmTermsBtn = document.getElementById("confirmRegisterTerms");
  var termsDot = document.querySelector("#termsConsent .terms-status-dot");

  var termsTimer = null;
  var termsRemain = 5;

  function renderTermsBtn() {
    if (!confirmTermsBtn) return;
    confirmTermsBtn.disabled = termsRemain > 0;
    confirmTermsBtn.textContent = termsRemain > 0 ? "请阅读 " + termsRemain + "s" : "我已阅读并同意";
  }

  if (openTermsBtn && termsModal) {
    openTermsBtn.addEventListener("click", function() {
      termsRemain = 5;
      renderTermsBtn();
      termsModal.style.display = "flex";
      document.body.classList.add("modal-open");
      if (termsTimer) clearInterval(termsTimer);
      termsTimer = setInterval(function() {
        termsRemain -= 1;
        if (termsRemain <= 0) {
          clearInterval(termsTimer);
          termsRemain = 0;
        }
        renderTermsBtn();
      }, 1000);
    });
  }

  if (confirmTermsBtn && termsModal) {
    confirmTermsBtn.addEventListener("click", function() {
      if (termsRemain > 0) return;
      termsAccepted = true;
      termsModal.style.display = "none";
      document.body.classList.remove("modal-open");
      if (termsRemain) clearInterval(termsTimer);
      if (termsDot) termsDot.classList.add("accepted");
    });
  }

  if (termsModal) {
    termsModal.addEventListener("click", function(e) {
      if (e.target === termsModal) {
        termsModal.style.display = "none";
        document.body.classList.remove("modal-open");
        if (termsRemain) clearInterval(termsTimer);
      }
    });
  }

  // Send code
  if (sendCodeBtn) {
    sendCodeBtn.addEventListener("click", async function() {
      if (codeCountdown > 0) return;
      var email = document.getElementById("email").value.trim();
      if (!email) {
        showNotice("请先输入邮箱地址", "error");
        return;
      }
      sendCodeBtn.disabled = true;
      try {
        await postJson("/api/v1/auth/send-code", { email: email, purpose: "register" });
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

  // Submit
  if (!form) return;

  form.addEventListener("submit", async function(e) {
    e.preventDefault();

    if (!termsAccepted) {
      showNotice("请先阅读并同意用户协议", "error");
      return;
    }

    var username = document.getElementById("username").value.trim();
    var password = document.getElementById("campus_password").value;
    var email = document.getElementById("email").value.trim();
    var code = document.getElementById("email_code").value.trim();
    var inviteCode = document.getElementById("invite_code").value.trim();

    if (!username || !password || !email || !code || !inviteCode) {
      showNotice("请填写所有字段", "error");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "注册中...";

    try {
      await postJson("/api/v1/auth/register", {
        invite_code: inviteCode,
        username: username,
        campus_password: password,
        email: email,
        email_code: code
      });
      window.location.href = "/dashboard";
    } catch (error) {
      showNotice(error.message || "注册失败", "error");
      submitBtn.disabled = false;
      submitBtn.textContent = "注册并登录";
    }
  });
})();
