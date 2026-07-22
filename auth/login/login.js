// Password visibility toggle
const passwordToggle = document.getElementById('passwordToggle');
const passwordInput = document.getElementById('password');
const iconEye = passwordToggle.querySelector('.icon-eye');
const iconEyeOff = passwordToggle.querySelector('.icon-eye-off');

passwordToggle.addEventListener('click', () => {
    const isPassword = passwordInput.type === 'password';
    passwordInput.type = isPassword ? 'text' : 'password';
    iconEye.style.display = isPassword ? 'none' : 'block';
    iconEyeOff.style.display = isPassword ? 'block' : 'none';
    passwordInput.focus();
});

// Form submit handler (demo)
const loginForm = document.getElementById('loginForm');

loginForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value.trim();
    const password = passwordInput.value.trim();

    if (!email) {
        document.getElementById('email').focus();
        return;
    }
    if (!password) {
        passwordInput.focus();
        return;
    }

    // Demo: show success state
    const btn = loginForm.querySelector('.login-btn');
    btn.textContent = 'Logging in...';
    btn.style.opacity = '0.8';
    btn.disabled = true;

    setTimeout(() => {
        btn.textContent = 'Log In';
        btn.style.opacity = '1';
        btn.disabled = false;
    }, 2000);
});
