# 💊 MedAsis — AI-Powered Medicine Assistant

An intelligent medicine inventory manager that extracts structured data from medicine packaging images using **OCR.space** and **Google Gemini**, stores it in a vector database, and lets you query your inventory using natural-language questions via a **RAG (Retrieval-Augmented Generation)** pipeline.

---

## ✨ Features

- **📸 Image-Based Data Extraction** — Upload a photo of any medicine label. OCR.space extracts the text, and Gemini structures it into clean metadata (name, dose, expiry, manufacturer, batch no.).
- **🧠 RAG-Powered Chat** — Ask natural-language questions like *"Do I have any paracetamol?"* or *"Which medicines are expiring soon?"* and get AI-generated answers grounded in your actual inventory.
- **⚠️ Smart Expiry Tracking** — Automatically flags medicines that are expired or expiring within 30/90 days with color-coded alerts.
- **📋 Inventory Dashboard** — View, manage, and delete all stored medicines with real-time stats (total, valid, expiring, expired).
- **🔄 Duplicate Detection** — Re-uploading a medicine with the same name updates the existing record instead of creating duplicates.
- **🌙 Premium Dark UI** — Glassmorphic, responsive interface built with vanilla HTML/CSS/JS.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python, Flask |
| **OCR** | [OCR.space API](https://ocr.space/ocrapi) (Engine 2 with Engine 1 fallback) |
| **LLM** | Google Gemini (`gemini-3-flash-preview`) |
| **Vector DB** | ChromaDB (persistent, cosine similarity) |
| **Embeddings** | Sentence Transformers (ChromaDB default) |
| **Frontend** | HTML, CSS (glassmorphism dark theme), Vanilla JS |
| **Markdown** | Marked.js (for rendering chat responses) |

---

## 📁 Project Structure

```
Medstore/
├── app.py               # Flask application — routes & API endpoints
├── medicine_rag.py      # RAG engine — vector DB, querying, expiry logic
├── ocr_utils.py         # OCR.space + Gemini text structuring pipeline
├── requirements.txt     # Python dependencies
├── .env                 # API keys (not committed)
├── templates/
│   └── index.html       # Main UI template
├── static/
│   ├── style.css        # Premium dark theme styles
│   └── app.js           # Frontend logic (upload, chat, inventory)
├── medicine_db/         # ChromaDB persistent storage (auto-created)
└── uploads/             # Uploaded medicine images (auto-created)
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- [OCR.space API Key](https://ocr.space/ocrapi) (free tier available)
- [Google Gemini API Key](https://aistudio.google.com/apikey)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/<your-username>/MedAsis.git
   cd MedAsis
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux/macOS
   venv\Scripts\activate         # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the project root:

   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   OCR_SPACE_API_KEY=your_ocr_space_api_key_here
   ```

5. **Run the application**

   ```bash
   python app.py
   ```

   Open **http://localhost:5000** in your browser.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serve the web UI |
| `POST` | `/upload` | Upload a medicine image → OCR → store |
| `POST` | `/query` | Ask a natural-language question (RAG) |
| `GET` | `/medicines` | List all medicines with expiry status |
| `DELETE` | `/medicines/<id>` | Delete a medicine by ID |
| `GET` | `/expiring?days=30` | Get expiring & expired medicines |

---

## 🔧 How It Works

```
┌──────────────┐     ┌────────────┐     ┌─────────────┐     ┌──────────┐
│ Medicine     │────▶│ OCR.space  │────▶│ Gemini LLM  │────▶│ ChromaDB │
│ Image Upload │     │ (raw text) │     │ (structured │     │ (vector  │
│              │     │            │     │   JSON)     │     │  store)  │
└──────────────┘     └────────────┘     └─────────────┘     └──────────┘
                                                                  │
┌──────────────┐     ┌────────────┐     ┌─────────────┐           │
│ User         │────▶│ Similarity │────▶│ Gemini RAG  │◀──────────┘
│ Question     │     │  Search    │     │ (answer gen) │
└──────────────┘     └────────────┘     └─────────────┘
```

1. **Upload** — Image is sent to OCR.space (Engine 2, with Engine 1 fallback) to extract raw text.
2. **Structure** — Gemini parses the OCR text into a structured JSON object with medicine fields.
3. **Store** — The structured data is embedded and stored in ChromaDB with cosine similarity indexing.
4. **Query** — User questions are vector-searched against stored medicines. Matching results + the question are sent to Gemini for a natural-language answer.
5. **Expiry** — Dates are standardized to `MM/YYYY` and continuously checked against the current date.

---

## 📸 Screenshots

<!-- Add your screenshots here -->
<!-- ![Upload Tab](screenshots/upload.png) -->
<!-- ![Chat Tab](screenshots/chat.png) -->
<!-- ![Inventory Tab](screenshots/inventory.png) -->

---

## 📝 License

This project is open-source and available under the [MIT License](LICENSE).

---

> Built with ❤️ using Flask, OCR.space, Google Gemini, and ChromaDB.
