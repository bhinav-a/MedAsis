import cv2
import numpy as np
import easyocr
import os

# Debug: check current folder
print("Current Directory:", os.getcwd())

# Load image (change path if needed)
img = cv2.imread('image.png')

# Safety check
if img is None:
    print("❌ Image not found! Check file name/path.")
    exit()

# Resize (important for small text)
img = cv2.resize(img, None, fx=2, fy=2)

# Convert to grayscale
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Apply adaptive threshold to handle uneven lighting (prevents large black patches)
# Block size 51 and C=15 are good defaults for text on white background with some shadow
thresh = cv2.adaptiveThreshold(
    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 15
)

# Save processed image (optional)
cv2.imwrite('processed1.png', thresh)

# Initialize EasyOCR (GPU enabled)
reader = easyocr.Reader(['en'], gpu=True)

# OCR
result = reader.readtext(
    thresh,
    detail=0,
    paragraph=True,
    contrast_ths=0.05,
    adjust_contrast=0.7,
    text_threshold=0.4,
    low_text=0.2
)

# Print extracted text
print("\nExtracted Text:\n")
for line in result:
    print(line)