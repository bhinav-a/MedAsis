import os
import json
import re
from datetime import timedelta
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from medicine_rag import MedicineRAG
from functools import wraps
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=int(os.getenv('SESSION_LIFETIME_HOURS', '12')))
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if SUPABASE_URL and (SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY):
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY)
else:
    supabase = None
    print("⚠️  Warning: Supabase credentials not configured. Authentication will not work.")

# Initialize RAG system
rag = MedicineRAG()


# ── Authentication Decorator ──────────────────────────────────────────

def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def api_login_required(f):
    """Decorator to require login for API routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def is_valid_full_name(name):
    """Allow letters, spaces, apostrophes, dots, and hyphens only."""
    return bool(name) and bool(re.match(r"^[A-Za-z][A-Za-z\s'.-]{1,49}$", name))


# ── Authentication Routes ─────────────────────────────────────────────

@app.route('/login')
def login():
    """Render login page."""
    if 'user_id' in session:
        return redirect(url_for('app_home'))
    return render_template('auth.html')


@app.route('/reset-password')
def reset_password():
    """Render the password reset page."""
    return render_template(
        'reset_password.html',
        supabase_url=SUPABASE_URL or '',
        supabase_key=SUPABASE_KEY or ''
    )


@app.route('/api/auth/reset-password', methods=['POST'])
def auth_reset_password():
    """Send a Supabase password reset email."""
    if not supabase:
        return jsonify({"error": "Authentication service not configured"}), 503

    data = request.get_json() or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({"error": "Email is required", "field": "email"}), 400

    try:
        redirect_url = url_for('reset_password', _external=True)
        supabase.auth.reset_password_for_email(email, {"redirect_to": redirect_url})
        return jsonify({
            "success": True,
            "message": "If the email exists, a password reset link has been sent."
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/auth/signin', methods=['POST'])
def auth_signin():
    """Sign in user with email and password."""
    if not supabase:
        return jsonify({"error": "Authentication service not configured"}), 503

    data = request.get_json()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email:
        return jsonify({"error": "Email is required", "field": "email"}), 400
    if not password:
        return jsonify({"error": "Password is required", "field": "password"}), 400

    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        user = response.user
        session.clear()
        session.permanent = True
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_name'] = user.user_metadata.get('name', '') if user.user_metadata else ''
        return jsonify({
            "success": True,
            "message": "Signed in successfully",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": session['user_name']
            }
        }), 200
    except Exception as e:
        error_msg = str(e)
        if 'Email not confirmed' in error_msg:
            return jsonify({"error": "Please verify your email before signing in."}), 401
        if 'Invalid login credentials' in error_msg:
            return jsonify({"error": "Invalid email or password"}), 401
        return jsonify({"error": error_msg}), 400


@app.route('/api/auth/signup', methods=['POST'])
def auth_signup():
    """Sign up new user."""
    if not supabase:
        return jsonify({"error": "Authentication service not configured"}), 503

    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not name:
        return jsonify({"error": "Name is required", "field": "name"}), 400
    if not is_valid_full_name(name):
        return jsonify({"error": "Use letters only. Numbers are not allowed.", "field": "name"}), 400
    if not email:
        return jsonify({"error": "Email is required", "field": "email"}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters", "field": "password"}), 400

    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {"name": name}
            }
        })
        user = response.user

        # If email confirmations are enabled in Supabase, the user must verify before login.
        if getattr(user, 'email_confirmed_at', None):
            session.clear()
            session.permanent = True
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['user_name'] = name
            message = "Account created successfully"
        else:
            message = "Account created. Check your email to verify your account before signing in."

        return jsonify({
            "success": True,
            "message": message,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": name
            }
        }), 201
    except Exception as e:
        error_msg = str(e)
        if 'already registered' in error_msg.lower():
            return jsonify({"error": "Email already registered", "field": "email"}), 400
        if 'password' in error_msg.lower():
            return jsonify({"error": "Password does not meet requirements", "field": "password"}), 400
        return jsonify({"error": error_msg}), 400


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """Logout user."""
    if supabase and 'user_id' in session:
        try:
            supabase.auth.sign_out()
        except:
            pass
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"}), 200


@app.route('/api/auth/user', methods=['GET'])
def auth_user():
    """Get current user info."""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({
        "user_id": session.get('user_id'),
        "email": session.get('user_email'),
        "name": session.get('user_name')
    }), 200


# ── Pages ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Redirect to app or login."""
    if 'user_id' in session:
        return redirect(url_for('app_home'))
    return redirect(url_for('login'))


@app.route('/app')
@login_required
def app_home():
    """Main app page (requires login)."""
    return render_template('index.html')


# ── API Routes ────────────────────────────────────────────────────────

@app.route('/upload', methods=['POST'])
@api_login_required
def upload_medicine():
    """Upload a medicine image, run OCR, store in DB."""
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        user_id = session.get('user_id')
        medicine_info, expiry_info, is_update = rag.add_medicine_from_image(filepath, user_id=user_id)
        return jsonify({
            "success": True,
            "is_update": is_update,
            "medicine": {
                "name": medicine_info.get("name") or "Unknown",
                "mfd": medicine_info.get("mfd") or "N/A",
                "exp_date": medicine_info.get("exp_date") or "N/A",
                "dose": medicine_info.get("dose") or "N/A",
                "batch_no": medicine_info.get("batch_no") or "N/A",
                "manufacturer": medicine_info.get("manufacturer") or "N/A",
            },
            "expiry": expiry_info,
            "message": (
                f"Medicine {'updated' if is_update else 'added'} successfully!"
                + (f" ⚠️ Expires in {expiry_info['days']} days!" if expiry_info['status'] == 'expiring_soon' else "")
                + (f" 🚨 This medicine is EXPIRED!" if expiry_info['status'] == 'expired' else "")
            )
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/query', methods=['POST'])
@api_login_required
def query_medicine():
    """Ask a question about medicines using RAG."""
    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({"error": "No question provided"}), 400

    question = data['question'].strip()
    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    try:
        result = rag.ask(question, user_id=session.get('user_id'))
        return jsonify({
            "success": True,
            "answer": result["answer"],
            "sources": result["sources"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/medicines', methods=['GET'])
@api_login_required
def list_medicines():
    """List all medicines in the database."""
    try:
        medicines = rag.list_all_medicines(user_id=session.get('user_id'))
        return jsonify({
            "success": True,
            "medicines": medicines,
            "count": len(medicines),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/medicines/<med_id>', methods=['DELETE'])
@api_login_required
def delete_medicine(med_id):
    """Delete a medicine by ID."""
    try:
        rag.delete_medicine(med_id, user_id=session.get('user_id'))
        return jsonify({"success": True, "message": f"Medicine {med_id} deleted."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/expiring', methods=['GET'])
@api_login_required
def expiring_medicines():
    """Get medicines expiring within N days (default 30)."""
    days = request.args.get('days', 30, type=int)
    try:
        user_id = session.get('user_id')
        expiring = rag.get_expiring_medicines(days, user_id=user_id)
        expired = rag.get_expired_medicines(user_id=user_id)
        return jsonify({
            "success": True,
            "expiring": expiring,
            "expired": expired,
            "expiring_count": len(expiring),
            "expired_count": len(expired),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
