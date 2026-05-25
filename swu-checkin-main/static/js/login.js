(function() {
  var form = document.getElementById("loginForm");
  var submitBtn = document.getElementById("submitBtn");
  var termsAccepted = false;

  // Terms modal for login
  var termsModal = document.getElementById("loginTermsModal");
  var openTermsBtn = document.getElementById("openLoginTermsModal");
  var confirmTermsBtn = document.getElementById("confirmLoginTerms");
  var termsDot = document.querySelector("#loginTermsConsent .terms-status-dot");

  if (openTermsBtn && termsModal) {
    openTermsBtn.addEventListener("click", function() {
      termsModal.style.display = "flex";
      document.body.classList.add("modal-open");
    });
  }

  if (confirmTermsBtn && termsModal) {
    confirmTermsBtn.addEventListener("click", function() {
      termsAccepted = true;
      termsModal.style.display = "none";
      document.body.classList.remove("modal-open");
      if (termsDot) termsDot.classList.add("accepted");
    });
  }

  // Close modal on overlay click
  if (termsModal) {
    termsModal.addEventListener("click", function(e) {
      if (e.target === termsModal) {
        termsModal.style.display = "none";
        document.body.classList.remove("modal-open");
      }
    });
  }

  if (!form) return;

  form.addEventListener("submit", async function(e) {
    e.preventDefault();

    if (!termsAccepted) {
      showNotice("请先阅读并同意用户协议", "error");
      return;
    }

    var username = document.getElementById("username").value.trim();
    var password = document.getElementById("campus_password").value;

    if (!username || !password) {
      showNotice("请输入校园网账号和密码", "error");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "登录中...";

    try {
      await postJson("/api/v1/auth/login", {
        username: username,
        campus_password: password
      });
      var next = new URLSearchParams(window.location.search).get("next") || "/dashboard";
      window.location.href = next;
    } catch (error) {
      showNotice(error.message || "登录失败", "error");
      submitBtn.disabled = false;
      submitBtn.textContent = "登录";
    }
  });
})();
