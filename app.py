import os
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from medicine_rag import MedicineRAG

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize RAG system
rag = MedicineRAG()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Pages ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


# ── API Routes ────────────────────────────────────────────────────────

@app.route('/upload', methods=['POST'])
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
        medicine_info, expiry_info, is_update = rag.add_medicine_from_image(filepath)
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
def query_medicine():
    """Ask a question about medicines using RAG."""
    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({"error": "No question provided"}), 400

    question = data['question'].strip()
    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    try:
        result = rag.ask(question)
        return jsonify({
            "success": True,
            "answer": result["answer"],
            "sources": result["sources"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/medicines', methods=['GET'])
def list_medicines():
    """List all medicines in the database."""
    try:
        medicines = rag.list_all_medicines()
        return jsonify({
            "success": True,
            "medicines": medicines,
            "count": len(medicines),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/medicines/<med_id>', methods=['DELETE'])
def delete_medicine(med_id):
    """Delete a medicine by ID."""
    try:
        rag.delete_medicine(med_id)
        return jsonify({"success": True, "message": f"Medicine {med_id} deleted."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/expiring', methods=['GET'])
def expiring_medicines():
    """Get medicines expiring within N days (default 30)."""
    days = request.args.get('days', 30, type=int)
    try:
        expiring = rag.get_expiring_medicines(days)
        expired = rag.get_expired_medicines()
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
