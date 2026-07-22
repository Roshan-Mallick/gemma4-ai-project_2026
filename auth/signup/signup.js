// Password visibility toggle
function setupPasswordToggle(toggleId, inputId) {
    const toggle = document.getElementById(toggleId);
    const input = document.getElementById(inputId);
    const iconEye = toggle.querySelector('.icon-eye');
    const iconEyeOff = toggle.querySelector('.icon-eye-off');

    toggle.addEventListener('click', () => {
        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        iconEye.style.display = isPassword ? 'none' : 'block';
        iconEyeOff.style.display = isPassword ? 'block' : 'none';
        input.focus();
    });
}

setupPasswordToggle('passwordToggle', 'password');
setupPasswordToggle('confirmPasswordToggle', 'confirmPassword');

// Password match validation
const passwordInput = document.getElementById('password');
const confirmPasswordInput = document.getElementById('confirmPassword');
const passwordError = document.getElementById('passwordError');

function checkPasswordMatch() {
    const password = passwordInput.value;
    const confirm = confirmPasswordInput.value;

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

// Form submit handler
const signupForm = document.getElementById('signupForm');

signupForm.addEventListener('submit', (e) => {
    e.preventDefault();

    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = passwordInput.value.trim();
    const confirm = confirmPasswordInput.value.trim();
    const terms = document.getElementById('terms').checked;

    if (!username) {
        document.getElementById('username').focus();
        return;
    }
    if (!email) {
        document.getElementById('email').focus();
        return;
    }
    if (!password) {
        passwordInput.focus();
        return;
    }
    if (password !== confirm) {
        confirmPasswordInput.focus();
        return;
    }
    if (!terms) {
        document.getElementById('terms').focus();
        return;
    }

    const btn = signupForm.querySelector('.login-btn');
    btn.textContent = 'Creating account...';
    btn.style.opacity = '0.8';
    btn.disabled = true;

    setTimeout(() => {
        btn.textContent = 'Create Account';
        btn.style.opacity = '1';
        btn.disabled = false;
    }, 2000);
});
