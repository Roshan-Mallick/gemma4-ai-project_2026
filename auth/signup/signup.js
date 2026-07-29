function setupPasswordToggle(toggleId, inputId) {
    var toggle = document.getElementById(toggleId);
    var input = document.getElementById(inputId);
    if (!toggle || !input) return;

    var iconEye = toggle.querySelector('.icon-eye');
    var iconEyeOff = toggle.querySelector('.icon-eye-off');

    toggle.addEventListener('click', function () {
        var isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        if (iconEye) iconEye.style.display = isPassword ? 'none' : 'block';
        if (iconEyeOff) iconEyeOff.style.display = isPassword ? 'block' : 'none';
        toggle.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
        input.focus();
    });
}

setupPasswordToggle('passwordToggle', 'password');
setupPasswordToggle('confirmPasswordToggle', 'confirmPassword');

var passwordInput = document.getElementById('password');
var confirmPasswordInput = document.getElementById('confirmPassword');
var passwordError = document.getElementById('passwordError');

if (passwordInput && confirmPasswordInput && passwordError) {
    function checkPasswordMatch() {
        var password = passwordInput.value;
        var confirm = confirmPasswordInput.value;

        if (confirm.length === 0) {
            passwordError.textContent = '';
            confirmPasswordInput.classList.remove('input-error');
            return;
        }

        if (password !== confirm) {
            passwordError.textContent = 'Passwords do not match';
            confirmPasswordInput.classList.add('input-error');
        } else {
            passwordError.textContent = '';
            confirmPasswordInput.classList.remove('input-error');
        }
    }

    passwordInput.addEventListener('input', checkPasswordMatch);
    confirmPasswordInput.addEventListener('input', checkPasswordMatch);
}

var signupForm = document.getElementById('signupForm');

if (signupForm) {
    signupForm.addEventListener('submit', function (e) {
        e.preventDefault();

        var username = document.getElementById('username');
        var email = document.getElementById('email');
        var terms = document.getElementById('terms');
        var usernameVal = username ? username.value.trim() : '';
        var emailVal = email ? email.value.trim() : '';
        var passwordVal = passwordInput ? passwordInput.value.trim() : '';
        var confirmVal = confirmPasswordInput ? confirmPasswordInput.value.trim() : '';
        var termsChecked = terms ? terms.checked : false;

        if (!usernameVal) { if (username) username.focus(); return; }
        if (!emailVal) { if (email) email.focus(); return; }
        if (!passwordVal) { if (passwordInput) passwordInput.focus(); return; }
        if (passwordVal !== confirmVal) { if (confirmPasswordInput) confirmPasswordInput.focus(); return; }
        if (!termsChecked) { if (terms) terms.focus(); return; }

        var btn = signupForm.querySelector('.login-btn');
        if (!btn) return;
        btn.textContent = 'Creating account...';
        btn.style.opacity = '0.8';
        btn.disabled = true;

        setTimeout(function () {
            btn.textContent = 'Create Account';
            btn.style.opacity = '1';
            btn.disabled = false;
        }, 2000);
    });
}
