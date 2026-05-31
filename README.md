# AI-Generated Image Evaluation System

## Layer 1 — JSON Validation
- Checks the JSON file is valid and parseable
- Verifies canvas dimensions are present
- Confirms exactly 1 name placeholder exists
- Confirms exactly 1 circular photo placeholder exists
- Validates name placeholder area is between 5–10% of canvas
- Validates photo placeholder area is between 25–30% of canvas (using πr²)

## Layer 2 — Image Validation
- Verifies the image file opens correctly
- Checks image dimensions match the JSON canvas size
- Runs OCR (Tesseract) to extract and verify text in the design
- Uses OpenCV Hough Circle Transform to detect circular placeholders visually

## Install Dependencies
```
py -m pip install pillow opencv-python pytesseract
```
