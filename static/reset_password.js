const resetAlert = document.getElementById('reset-alert');
const newPasswordForm = document.getElementById('new-password-form');
const newPasswordBtn = document.getElementById('new-password-btn');
const supabaseClient = window.supabase.createClient(window.SUPABASE_URL, window.SUPABASE_KEY);

function showAlert(message, type = 'error') {
    resetAlert.textContent = message;
    resetAlert.className = `alert alert-${type} show`;
}

function showFieldError(fieldId, message) {
    const errorEl = document.getElementById(`${fieldId}-error`);
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.add('show');
    }
}

function clearErrors() {
    document.querySelectorAll('.form-error').forEach(el => {
        el.textContent = '';
        el.classList.remove('show');
    });
    resetAlert.className = 'alert';
    resetAlert.textContent = '';
}

window.addEventListener('load', async () => {
    try {
        const { data, error } = await supabaseClient.auth.getSession();
        if (error || !data.session) {
            showAlert('This reset link is invalid or expired. Please request a new one.', 'error');
            newPasswordBtn.disabled = true;
            return;
        }
        showAlert('Link verified. Enter your new password.', 'success');
    } catch (error) {
        showAlert('Unable to verify reset link. Please request a new one.', 'error');
        newPasswordBtn.disabled = true;
    }
});

newPasswordForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearErrors();

    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;

    if (!newPassword) {
        showFieldError('new-password', 'New password is required');
        return;
    }
    if (newPassword.length < 6) {
        showFieldError('new-password', 'Password must be at least 6 characters');
        return;
    }
    if (newPassword !== confirmPassword) {
        showFieldError('confirm-password', 'Passwords do not match');
        return;
    }

    newPasswordBtn.disabled = true;
    newPasswordBtn.textContent = 'Updating...';

    try {
        const { error } = await supabaseClient.auth.updateUser({ password: newPassword });
        if (error) {
            showAlert(error.message || 'Could not update password.', 'error');
            return;
        }

        showAlert('Password updated successfully. Redirecting to login...', 'success');
        setTimeout(() => {
            window.location.href = '/login';
        }, 2000);
    } catch (error) {
        showAlert(error.message || 'Could not update password.', 'error');
    } finally {
        newPasswordBtn.disabled = false;
        newPasswordBtn.textContent = 'Update Password';
    }
});
