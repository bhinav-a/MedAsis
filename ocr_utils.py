import os
import json
import re
import requests
from dotenv import load_dotenv

load_dotenv()

# OCR.space API key
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY", "K88815191088957")


def extract_text_from_image(image_path):
    """
    Extract raw text from an image using OCR.space API.
    Returns the full detected text as a string.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    payload = {
        'isOverlayRequired': False,
        'apikey': OCR_SPACE_API_KEY,
        'language': 'eng',
        'scale': True,
        'isTable': False,
        'OCREngine': 2,  # Engine 2 is better for dense text
    }

    with open(image_path, 'rb') as f:
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files={os.path.basename(image_path): f},
            data=payload,
            timeout=30,
        )

    result = json.loads(response.content.decode())

    if result.get('OCRExitCode') == 1 and result.get('ParsedResults'):
        raw_text = result['ParsedResults'][0].get('ParsedText', '')
        print(f"✅ OCR.space extracted text ({len(raw_text)} chars)")
        return raw_text
    else:
        error = result.get('ErrorMessage') or result.get('ErrorDetails', 'Unknown error')
        # Try with Engine 1 as fallback
        payload['OCREngine'] = 1
        with open(image_path, 'rb') as f:
            response = requests.post(
                'https://api.ocr.space/parse/image',
                files={os.path.basename(image_path): f},
                data=payload,
                timeout=30,
            )
        result = json.loads(response.content.decode())
        if result.get('OCRExitCode') == 1 and result.get('ParsedResults'):
            raw_text = result['ParsedResults'][0].get('ParsedText', '')
            print(f"✅ OCR.space (Engine 1 fallback) extracted text ({len(raw_text)} chars)")
            return raw_text
        raise Exception(f"OCR.space error: {error}")


def extract_medicine_from_image(image_path):
    """
    Extract structured medicine information from an image.
    Step 1: OCR.space extracts clean text
    Step 2: Gemini structures the text into JSON
    Falls back to regex parsing if Gemini is unavailable.
    """
    # Step 1: Get raw text from OCR.space
    raw_text = extract_text_from_image(image_path)
    print(f"📝 OCR text:\n{raw_text[:300]}...")

    if not raw_text.strip():
        return {
            "name": None, "mfd": None, "exp_date": None, "dose": None,
            "batch_no": None, "manufacturer": None, "raw_text": "", "other_info": []
        }

    # Step 2: Use Gemini to structure the text
    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("⚠️ GEMINI_API_KEY not set, using fallback parser")
            return _fallback_parse(raw_text)

        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        model = genai.GenerativeModel(model_name)

        prompt = f"""Extract medicine information from this OCR text from a medicine package.
Return ONLY a valid JSON object with these exact keys (use null if not found):

{{
    "name": "medicine brand name and/or generic name (e.g., 'Paracip-500 (Paracetamol 500mg)')",
    "mfd": "manufacturing date exactly as printed",
    "exp_date": "expiry date exactly as printed",
    "dose": "dosage/strength (e.g., 500mg)",
    "batch_no": "batch or lot number",
    "manufacturer": "manufacturer or marketing company name",
    "raw_text": "a cleaned-up readable version of the important text",
    "other_info": ["composition", "storage instructions", "price", "any other useful details"]
}}

OCR TEXT:
{raw_text}

Return ONLY the JSON, no markdown or code blocks."""

        response = model.generate_content(prompt)
        text = response.text.strip()

        # Clean markdown formatting if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        result = json.loads(text)

        # Ensure all keys exist
        defaults = {
            "name": None, "mfd": None, "exp_date": None, "dose": None,
            "batch_no": None, "manufacturer": None, "raw_text": raw_text, "other_info": []
        }
        for key, default in defaults.items():
            if key not in result:
                result[key] = default

        return result

    except Exception as e:
        print(f"⚠️ Gemini structuring failed ({e}), using fallback parser")
        return _fallback_parse(raw_text)


def _fallback_parse(raw_text):
    """Simple regex-based fallback parser when Gemini is unavailable."""
    info = {
        "name": None, "mfd": None, "exp_date": None, "dose": None,
        "batch_no": None, "manufacturer": None, "raw_text": raw_text, "other_info": []
    }

    # Expiry
    exp_match = re.search(r'(?:EXP|Expiry|Exp)[.\s:]*([A-Z]{3}[\s./]*\d{2,4}|\d{2}[-/]\d{2,4})', raw_text, re.IGNORECASE)
    if exp_match:
        info["exp_date"] = exp_match.group(1).strip()

    # MFD
    mfd_match = re.search(r'(?:MFD|Mfg)[.\s:]*([A-Z]{3}[\s./]*\d{2,4}|\d{2}[-/]\d{2,4})', raw_text, re.IGNORECASE)
    if mfd_match:
        info["mfd"] = mfd_match.group(1).strip()

    # Dose
    dose_match = re.search(r'(\d+\s*(?:mg|g|ml|mcg))', raw_text, re.IGNORECASE)
    if dose_match:
        info["dose"] = dose_match.group(1).strip()

    # Batch
    batch_match = re.search(r'(?:B\.?\s*No|Batch|Lot)[.\s:#]*([A-Z0-9]+)', raw_text, re.IGNORECASE)
    if batch_match:
        info["batch_no"] = batch_match.group(1).strip()

    # Name - first meaningful line
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    if lines:
        info["name"] = lines[0][:60]

    return info