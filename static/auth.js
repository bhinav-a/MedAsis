// ═══════════════════════════════════════════════════════════════════
// Supabase Authentication Handler
// ═══════════════════════════════════════════════════════════════════

// Toggle between Sign In and Sign Up
function toggleAuth() {
    const signinSection = document.getElementById('signin-section');
    const signupSection = document.getElementById('signup-section');
    const resetSection = document.getElementById('reset-section');

    const showSignup = signinSection.classList.contains('active');
    signinSection.classList.toggle('active', !showSignup);
    signupSection.classList.toggle('active', showSignup);
    resetSection?.classList.remove('active');

    // Clear forms and errors
    document.getElementById('signin-form').reset();
    document.getElementById('signup-form').reset();
    document.getElementById('reset-form')?.reset();
    clearAllErrors();
    clearAlert();
}

function showSignInForm() {
    setActiveSection('signin-section');
}

function showResetForm() {
    setActiveSection('reset-section');
}

function setActiveSection(sectionId) {
    ['signin-section', 'signup-section', 'reset-section'].forEach(id => {
        const section = document.getElementById(id);
        if (section) {
            section.classList.toggle('active', id === sectionId);
        }
    });

    document.getElementById('signin-form')?.reset();
    document.getElementById('signup-form')?.reset();
    document.getElementById('reset-form')?.reset();
    clearAllErrors();
    clearAlert();
}

// Clear all form errors
function clearAllErrors() {
    document.querySelectorAll('.form-error').forEach(el => {
        el.textContent = '';
        el.classList.remove('show');
    });
}

// Show alert message
function showAlert(message, type = 'error') {
    const alertEl = document.getElementById('auth-alert');
    alertEl.textContent = message;
    alertEl.className = `alert alert-${type} show`;
    
    if (type === 'success') {
        setTimeout(clearAlert, 3000);
    }
}

// Clear alert
function clearAlert() {
    const alertEl = document.getElementById('auth-alert');
    alertEl.className = 'alert';
    alertEl.textContent = '';
}

// Show field error
function showFieldError(fieldId, message) {
    const errorEl = document.getElementById(`${fieldId}-error`);
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.add('show');
    }
}

// Validate email format
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function isValidFullName(name) {
    const nameRegex = /^[A-Za-z][A-Za-z\s'.-]{1,49}$/;
    return nameRegex.test(name);
}

// Handle Sign In
document.getElementById('signin-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearAllErrors();
    clearAlert();

    const email = document.getElementById('signin-email').value.trim();
    const password = document.getElementById('signin-password').value;
    const btn = document.getElementById('signin-btn');

    // Validate
    if (!email) {
        showFieldError('signin-email', 'Email is required');
        return;
    }
    if (!isValidEmail(email)) {
        showFieldError('signin-email', 'Invalid email format');
        return;
    }
    if (!password) {
        showFieldError('signin-password', 'Password is required');
        return;
    }

    btn.disabled = true;
    btn.classList.add('loading');

    try {
        const response = await fetch('/api/auth/signin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (!response.ok) {
            if (data.field) {
                showFieldError(`signin-${data.field}`, data.error);
            } else {
                showAlert(data.error || 'Sign in failed', 'error');
            }
        } else {
            showAlert('Sign in successful! Redirecting...', 'success');
            setTimeout(() => {
                window.location.href = '/app';
            }, 1500);
        }
    } catch (error) {
        showAlert('An error occurred. Please try again.', 'error');
        console.error('Sign in error:', error);
    } finally {
        btn.disabled = false;
        btn.classList.remove('loading');
    }
});

// Handle Sign Up
document.getElementById('signup-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearAllErrors();
    clearAlert();

    const name = document.getElementById('signup-name').value.trim();
    const email = document.getElementById('signup-email').value.trim();
    const password = document.getElementById('signup-password').value;
    const confirm = document.getElementById('signup-confirm').value;
    const btn = document.getElementById('signup-btn');

    // Validate
    if (!name) {
        showFieldError('signup-name', 'Name is required');
        return;
    }
    if (name.length < 2) {
        showFieldError('signup-name', 'Name must be at least 2 characters');
        return;
    }
    if (!isValidFullName(name)) {
        showFieldError('signup-name', 'Use letters only. Numbers are not allowed.');
        return;
    }
    if (!email) {
        showFieldError('signup-email', 'Email is required');
        return;
    }
    if (!isValidEmail(email)) {
        showFieldError('signup-email', 'Invalid email format');
        return;
    }
    if (!password) {
        showFieldError('signup-password', 'Password is required');
        return;
    }
    if (password.length < 6) {
        showFieldError('signup-password', 'Password must be at least 6 characters');
        return;
    }
    if (password !== confirm) {
        showFieldError('signup-confirm', 'Passwords do not match');
        return;
    }

    btn.disabled = true;
    btn.classList.add('loading');

    try {
        const response = await fetch('/api/auth/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });

        const data = await response.json();

        if (!response.ok) {
            if (data.field) {
                showFieldError(`signup-${data.field}`, data.error);
            } else {
                showAlert(data.error || 'Sign up failed', 'error');
            }
        } else {
            showAlert(data.message || 'Account created! Please verify your email before signing in.', 'success');
            setTimeout(() => {
                window.location.href = '/login';
            }, 2500);
        }
    } catch (error) {
        showAlert('An error occurred. Please try again.', 'error');
        console.error('Sign up error:', error);
    } finally {
        btn.disabled = false;
        btn.classList.remove('loading');
    }
});

// Handle Reset Password Request
document.getElementById('reset-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearAllErrors();
    clearAlert();

    const resetEmail = document.getElementById('reset-email').value.trim();
    const btn = document.getElementById('reset-btn');

    if (!resetEmail) {
        showFieldError('reset-email', 'Email is required');
        return;
    }
    if (!isValidEmail(resetEmail)) {
        showFieldError('reset-email', 'Invalid email format');
        return;
    }

    btn.disabled = true;
    btn.classList.add('loading');

    try {
        const response = await fetch('/api/auth/reset-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: resetEmail })
        });

        const data = await response.json();

        if (!response.ok) {
            if (data.field) {
                showFieldError(`reset-${data.field}`, data.error);
            } else {
                showAlert(data.error || 'Password reset failed', 'error');
            }
        } else {
            showAlert(data.message || 'Reset email sent. Check your inbox.', 'success');
            setTimeout(() => setActiveSection('signin-section'), 2500);
        }
    } catch (error) {
        showAlert('An error occurred. Please try again.', 'error');
        console.error('Reset password error:', error);
    } finally {
        btn.disabled = false;
        btn.classList.remove('loading');
    }
});

// Check if user is already authenticated
window.addEventListener('load', async () => {
    try {
        const response = await fetch('/api/auth/user');
        if (response.ok) {
            // User is already logged in, redirect to app
            window.location.href = '/app';
        }
    } catch (error) {
        console.log('Not authenticated');
    }
});
