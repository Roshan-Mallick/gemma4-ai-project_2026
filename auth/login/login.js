var passwordToggle = document.getElementById('passwordToggle');
var passwordInput = document.getElementById('password');
var loginForm = document.getElementById('loginForm');

if (passwordToggle && passwordInput) {
    var iconEye = passwordToggle.querySelector('.icon-eye');
    var iconEyeOff = passwordToggle.querySelector('.icon-eye-off');

    passwordToggle.addEventListener('click', function () {
        var isPassword = passwordInput.type === 'password';
        passwordInput.type = isPassword ? 'text' : 'password';
        if (iconEye) iconEye.style.display = isPassword ? 'none' : 'block';
        if (iconEyeOff) iconEyeOff.style.display = isPassword ? 'block' : 'none';
        passwordToggle.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
        passwordInput.focus();
    });
}

if (loginForm) {
    loginForm.addEventListener('submit', function (e) {
        e.preventDefault();
        var email = document.getElementById('email');
        var emailVal = email ? email.value.trim() : '';
        var passwordVal = passwordInput ? passwordInput.value.trim() : '';

        if (!emailVal) {
            if (email) email.focus();
            return;
        }
        if (!passwordVal) {
            if (passwordInput) passwordInput.focus();
            return;
        }

        var btn = loginForm.querySelector('.login-btn');
        if (!btn) return;
        btn.textContent = 'Logging in...';
        btn.style.opacity = '0.8';
        btn.disabled = true;

        setTimeout(function () {
            btn.textContent = 'Log In';
            btn.style.opacity = '1';
            btn.disabled = false;
        }, 2000);
    });
}
