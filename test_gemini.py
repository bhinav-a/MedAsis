import os, json
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3-flash-preview")

ocr_text = """500 mg
proceramo labiets IP
ARACIP-500
th uncoated tablet contains
Dosage: Adults: 500 mg 197 90g 0g (Ito 2
acetamol IP
500 mg
B.NO CP10964 MFD.AUG.21 EXP.JUL.24 M.R.P.
DS10.02 FOR 10 TABS. (INCL. ALL TAXES)
Marketed by CIPLA LTD.
Manufactured by : HSNOVTN
Plot No. 40, Sector 6A, SIDCUL
Haridwar-249 403, (Uttarakhand)
Store below 30C. Protect from light.
Keep out of reach of children."""

prompt = (
    "Extract medicine information from this OCR text from a medicine package.\n"
    "Return ONLY a valid JSON object with these keys (use null if not found):\n"
    '{"name": "brand + generic", "mfd": "mfg date", "exp_date": "expiry date", '
    '"dose": "strength", "batch_no": "batch number", "manufacturer": "company", '
    '"raw_text": "cleaned text", "other_info": ["extra details"]}\n\n'
    "OCR TEXT:\n" + ocr_text + "\n\nReturn ONLY JSON, no markdown."
)

try:
    r = model.generate_content(prompt)
    print("=== GEMINI RESPONSE ===")
    print(r.text)
except Exception as e:
    print(f"Error: {e}")
