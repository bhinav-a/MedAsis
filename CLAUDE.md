# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Environment Setup
The project uses a Python virtual environment located at `venv`. To activate it:
- On Windows: `venv\Scripts\activate`
- On Unix/macOS: `source venv/bin/activate`

### Running OCR Scripts
Three OCR scripts are available, each expecting an input image named `image.png` in the project root:

1. **Basic EasyOCR** (`eocr.py`):
   ```bash
   python eocr.py
   ```
   Uses EasyOCR with default settings on the original image.

2. **Preprocessed EasyOCR** (`proeocr.py`):
   ```bash
   python proeocr.py
   ```
   Applies preprocessing (resize, grayscale, adaptive threshold) before EasyOCR with GPU enabled.

3. **Tesseract OCR** (`tesseract_ocr.py`):
   ```bash
   python tesseract_ocr.py
   ```
   Applies same preprocessing as `proeocr.py` then uses PyTesseract.
   If Tesseract is not in PATH, uncomment and set the `tesseract_cmd` path in the script.

### Dependencies
The virtual environment includes:
- easyocr
- opencv-python (cv2)
- pytesseract
- numpy

To install additional packages, use `pip install <package>` within the activated venv.

## Code Structure

### Core Functionality
All scripts perform OCR on medical document images (`image.png`) using different approaches:
- `eocr.py`: Direct EasyOCR application
- `proeocr.py`: Image preprocessing pipeline followed by EasyOCR (GPU accelerated)
- `tesseract_ocr.py`: Same preprocessing pipeline followed by Tesseract OCR

### Common Preprocessing Steps
The preprocessing pipeline in `proeocr.py` and `tesseract_ocr.py` includes:
1. Resizing image 2x (important for small text)
2. Converting to grayscale
3. Applying adaptive threshold (Gaussian method) to handle uneven lighting
4. Saving processed image (optional, outputs: `processed1.png` or `processed_tesseract.png`)

### File Naming Conventions
- Input image: `image.png` (expected in project root)
- Processed images: `processed1.png` (EasyOCR path) or `processed_tesseract.png` (Tesseract path)
- Output: Printed to console (extracted text lines)

## Notes
- The project appears focused on medical document text extraction (based on directory name and sample images)
- PDF reference (`2410.10594v2.pdf`) may contain related research but is not directly used in code
- All scripts are standalone and can be run independently