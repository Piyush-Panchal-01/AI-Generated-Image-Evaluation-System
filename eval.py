
import json
import os
import math
import webbrowser
from datetime import datetime
from pathlib import Path

# ── Optional imports (graceful degradation if not installed) ──
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("WARNING: Pillow not installed. Image checks will be skipped.")
    print("         Run: pip install pillow\n")

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("WARNING: OpenCV not installed. Circle detection will be skipped.")
    print("         Run: pip install opencv-python\n")

try:
    import pytesseract
    # ── CHANGE THIS PATH if Tesseract is installed elsewhere ──
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("WARNING: pytesseract not installed. OCR check will be skipped.")
    print("         Run: pip install pytesseract\n")



JSON_FILE  = "input/sample.json"  
IMAGE_FILE = "input/images.png"    
OUTPUT_DIR = "Output"


NAME_AREA_MIN  = 0.05   # 5%
NAME_AREA_MAX  = 0.10   # 10%
PHOTO_AREA_MIN = 0.25   # 25%
PHOTO_AREA_MAX = 0.30   # 30%
TOLERANCE      = 0.002  # ±0.2% floating-point buffer




def pct(value):
    return f"{value * 100:.2f}%"

def status_icon(passed):
    return "✅ PASS" if passed else "❌ FAIL"


# 
# 

def validate_json(json_path):
    results = []

    if not os.path.exists(json_path):
        return [{"check": "JSON file found", "passed": False,
                 "detail": f"File not found: {json_path}", "layer": "JSON"}]

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        results.append({"check": "JSON file is valid", "passed": True,
                        "detail": "File parsed successfully.", "layer": "JSON"})
    except json.JSONDecodeError as e:
        results.append({"check": "JSON file is valid", "passed": False,
                        "detail": f"JSON parse error: {e}", "layer": "JSON"})
        return results

    canvas = data.get("canvas", {})
    canvas_w = canvas.get("width")
    canvas_h = canvas.get("height")

    if canvas_w and canvas_h:
        canvas_area = canvas_w * canvas_h
        results.append({"check": "Canvas dimensions found", "passed": True,
                        "detail": f"Canvas: {canvas_w} × {canvas_h} px  (area = {canvas_area:,} px²)",
                        "layer": "JSON"})
    else:
        results.append({"check": "Canvas dimensions found", "passed": False,
                        "detail": "Missing 'canvas.width' or 'canvas.height' in JSON.", "layer": "JSON"})
        return results

    placeholders = data.get("placeholders", [])
    name_holders = [p for p in placeholders if p.get("type") == "name_placeholder"]
    count_ok = len(name_holders) == 1
    results.append({
        "check": "Exactly 1 name placeholder",
        "passed": count_ok,
        "detail": f"Found {len(name_holders)} name placeholder(s). Required: exactly 1.",
        "layer": "JSON"
    })

    if name_holders:
        np_box = name_holders[0].get("bounding_box", {})
        np_w = np_box.get("width", 0)
        np_h = np_box.get("height", 0)
        np_area_ratio = (np_w * np_h) / canvas_area if canvas_area else 0
        area_pass = (NAME_AREA_MIN - TOLERANCE) <= np_area_ratio <= (NAME_AREA_MAX + TOLERANCE)
        results.append({
            "check": f"Name placeholder area ({pct(NAME_AREA_MIN)}–{pct(NAME_AREA_MAX)})",
            "passed": area_pass,
            "detail": (f"Name box: {np_w}×{np_h} px → area ratio = {pct(np_area_ratio)}  "
                       f"(allowed: {pct(NAME_AREA_MIN)}–{pct(NAME_AREA_MAX)})"),
            "layer": "JSON"
        })
    else:
        results.append({"check": f"Name placeholder area ({pct(NAME_AREA_MIN)}–{pct(NAME_AREA_MAX)})",
                        "passed": False, "detail": "No name placeholder found to measure.",
                        "layer": "JSON"})

    photo_holders = [p for p in placeholders
                     if p.get("type") == "photo_placeholder" and p.get("shape") == "circle"]
    p_count_ok = len(photo_holders) == 1
    results.append({
        "check": "Exactly 1 circular photo placeholder",
        "passed": p_count_ok,
        "detail": f"Found {len(photo_holders)} circular photo placeholder(s). Required: exactly 1.",
        "layer": "JSON"
    })

    if photo_holders:
        radius = photo_holders[0].get("radius", 0)
        photo_area_ratio = (math.pi * radius ** 2) / canvas_area if canvas_area else 0
        photo_area_pass = (PHOTO_AREA_MIN - TOLERANCE) <= photo_area_ratio <= (PHOTO_AREA_MAX + TOLERANCE)
        results.append({
            "check": f"Photo placeholder area ({pct(PHOTO_AREA_MIN)}–{pct(PHOTO_AREA_MAX)})",
            "passed": photo_area_pass,
            "detail": (f"Circle radius = {radius} px → area = π×{radius}² = {math.pi * radius**2:,.0f} px²  "
                       f"→ ratio = {pct(photo_area_ratio)}  "
                       f"(allowed: {pct(PHOTO_AREA_MIN)}–{pct(PHOTO_AREA_MAX)})"),
            "layer": "JSON"
        })
    else:
        results.append({"check": f"Photo placeholder area ({pct(PHOTO_AREA_MIN)}–{pct(PHOTO_AREA_MAX)})",
                        "passed": False, "detail": "No circular photo placeholder found to measure.",
                        "layer": "JSON"})

    return results



def validate_image(image_path, json_path):
    results = []

    if not PIL_AVAILABLE:
        results.append({"check": "Image checks", "passed": False,
                        "detail": "Pillow library not installed. Run: pip install pillow",
                        "layer": "Image"})
        return results

    if not os.path.exists(image_path):
        results.append({"check": "Image file found", "passed": False,
                        "detail": f"File not found: {image_path}", "layer": "Image"})
        return results

    try:
        img = Image.open(image_path)
        img_w, img_h = img.size
        results.append({"check": "Image file is valid", "passed": True,
                        "detail": f"Opened successfully. Size: {img_w} × {img_h} px, Mode: {img.mode}",
                        "layer": "Image"})
    except Exception as e:
        results.append({"check": "Image file is valid", "passed": False,
                        "detail": f"Could not open image: {e}", "layer": "Image"})
        return results

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        canvas = data.get("canvas", {})
        json_w = canvas.get("width")
        json_h = canvas.get("height")
        if json_w and json_h:
            dim_match = (img_w == json_w and img_h == json_h)
            results.append({
                "check": "Image dimensions match JSON canvas",
                "passed": dim_match,
                "detail": f"Image: {img_w}×{img_h}  |  JSON canvas: {json_w}×{json_h}",
                "layer": "Image"
            })
    except Exception:
        pass

    if TESSERACT_AVAILABLE:
        try:
            ocr_config = r"--oem 3 --psm 3 -l eng+hin"
            raw_text = pytesseract.image_to_string(img, config=ocr_config).strip()
            has_text = len(raw_text) > 0
            results.append({
                "check": "OCR text extraction (wording)",
                "passed": has_text,
                "detail": (f"Extracted {len(raw_text)} characters via OCR. "
                           f"Preview: \"{raw_text[:120]}{'...' if len(raw_text) > 120 else ''}\""),
                "layer": "Image"
            })
        except Exception as e:
            results.append({"check": "OCR text extraction (wording)", "passed": False,
                            "detail": f"OCR failed: {e}. Check Tesseract is installed and path is correct.",
                            "layer": "Image"})
    else:
        results.append({"check": "OCR text extraction (wording)", "passed": False,
                        "detail": "pytesseract not installed. Run: pip install pytesseract",
                        "layer": "Image"})

    if CV2_AVAILABLE:
        try:
            img_cv = cv2.imread(image_path)
            gray   = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            gray   = cv2.medianBlur(gray, 5)
            circles = cv2.HoughCircles(
                gray, cv2.HOUGH_GRADIENT, dp=1.2,
                minDist=50,
                param1=100, param2=30,
                minRadius=int(min(img_w, img_h) * 0.1),
                maxRadius=int(min(img_w, img_h) * 0.45)
            )
            total_pixels = img_w * img_h
            if circles is not None:
                circles = np.round(circles[0, :]).astype("int")
                detected = []
                for (cx, cy, r) in circles:
                    ratio = (math.pi * r ** 2) / total_pixels
                    in_range = (PHOTO_AREA_MIN - TOLERANCE) <= ratio <= (PHOTO_AREA_MAX + TOLERANCE)
                    detected.append(f"centre ({cx},{cy}) radius {r} → {pct(ratio)} {'✓' if in_range else '✗'}")
                area_valid = any(
                    (PHOTO_AREA_MIN - TOLERANCE) <= (math.pi * r**2 / total_pixels) <= (PHOTO_AREA_MAX + TOLERANCE)
                    for (_, _, r) in circles
                )
                results.append({
                    "check": "Circular placeholder detected in image (25–30%)",
                    "passed": area_valid,
                    "detail": "Circles found: " + " | ".join(detected[:3]),
                    "layer": "Image"
                })
            else:
                results.append({"check": "Circular placeholder detected in image (25–30%)",
                                "passed": False,
                                "detail": "No circles detected in image. Check image contrast or placeholder colour.",
                                "layer": "Image"})
        except Exception as e:
            results.append({"check": "Circular placeholder detected in image (25–30%)",
                            "passed": False, "detail": f"OpenCV error: {e}", "layer": "Image"})
    else:
        results.append({"check": "Circular placeholder detected in image (25–30%)",
                        "passed": False,
                        "detail": "OpenCV not installed. Run: pip install opencv-python",
                        "layer": "Image"})

    return results




def build_report(json_results, image_results, json_path, image_path):
    all_results = json_results + image_results
    total   = len(all_results)
    passed  = sum(1 for r in all_results if r["passed"])
    failed  = total - passed
    overall = passed == total

    now = datetime.now().strftime("%d %b %Y, %I:%M %p")

    def row(r):
        color  = "#1a7f37" if r["passed"] else "#cf222e"
        bg     = "#f0fff4" if r["passed"] else "#fff5f5"
        icon   = "✅" if r["passed"] else "❌"
        badge  = "PASS"  if r["passed"] else "FAIL"
        badge_bg = "#1a7f37" if r["passed"] else "#cf222e"
        layer_color = "#0969da" if r["layer"] == "JSON" else "#8250df"
        return f"""
        <tr style="background:{bg}; border-bottom:1px solid #e5e7eb;">
          <td style="padding:12px 16px; font-size:14px;">
            <span style="background:{layer_color}; color:#fff; font-size:11px;
              padding:2px 8px; border-radius:20px; margin-right:8px;">{r['layer']}</span>
            {r['check']}
          </td>
          <td style="padding:12px 16px; text-align:center;">
            <span style="background:{badge_bg}; color:#fff; font-size:12px; font-weight:600;
              padding:3px 10px; border-radius:4px;">{icon} {badge}</span>
          </td>
          <td style="padding:12px 16px; font-size:13px; color:#555; font-family:monospace;">
            {r['detail']}
          </td>
        </tr>"""

    rows_html = "\n".join(row(r) for r in all_results)

    verdict_bg    = "#dcfce7" if overall else "#fee2e2"
    verdict_color = "#15803d" if overall else "#b91c1c"
    verdict_text  = "✅  ALL CHECKS PASSED — DESIGN APPROVED" if overall else f"❌  {failed} CHECK(S) FAILED — DESIGN REJECTED"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Eval Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #f8fafc; color: #1e293b; margin: 0; padding: 24px; }}
    .card {{ background: #fff; border-radius: 12px; box-shadow: 0 1px 4px rgba(0,0,0,.08);
             padding: 24px; margin-bottom: 20px; }}
    h1 {{ font-size: 22px; margin: 0 0 4px; }}
    .meta {{ font-size: 13px; color: #64748b; margin-bottom: 20px; }}
    .verdict {{ border-radius: 10px; padding: 18px 24px; font-size: 18px; font-weight: 700;
                text-align: center; letter-spacing: .3px;
                background: {verdict_bg}; color: {verdict_color}; margin-bottom: 20px; }}
    .stats {{ display: flex; gap: 16px; margin-bottom: 20px; }}
    .stat {{ flex: 1; background: #f1f5f9; border-radius: 8px; padding: 14px;
             text-align: center; }}
    .stat-num {{ font-size: 28px; font-weight: 700; }}
    .stat-label {{ font-size: 12px; color: #64748b; margin-top: 2px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th {{ background: #f1f5f9; padding: 10px 16px; text-align: left;
          font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing:.5px; }}
    .files {{ font-size: 13px; color: #475569; }}
    .files span {{ font-family: monospace; background: #f1f5f9;
                   padding: 2px 6px; border-radius: 4px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1> AI Design Eval Report</h1>
    <p class="meta">Generated: {now}</p>
    <p class="files">
      JSON: <span>{json_path}</span> &nbsp;|&nbsp; Image: <span>{image_path}</span>
    </p>
  </div>

  <div class="verdict">{verdict_text}</div>

  <div class="stats">
    <div class="stat">
      <div class="stat-num" style="color:#1e293b;">{total}</div>
      <div class="stat-label">Total Checks</div>
    </div>
    <div class="stat">
      <div class="stat-num" style="color:#15803d;">{passed}</div>
      <div class="stat-label">Passed</div>
    </div>
    <div class="stat">
      <div class="stat-num" style="color:#b91c1c;">{failed}</div>
      <div class="stat-label">Failed</div>
    </div>
    <div class="stat">
      <div class="stat-num" style="color:#0969da;">{int(passed/total*100) if total else 0}%</div>
      <div class="stat-label">Score</div>
    </div>
  </div>

  <div class="card">
    <table>
      <thead>
        <tr>
          <th style="width:38%">Check</th>
          <th style="width:10%; text-align:center">Result</th>
          <th>Detail</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>
</body>
</html>"""
    return html




def main():
    print("=" * 55)
    print("  MVP Eval System — starting…")
    print("=" * 55)

    json_results  = validate_json(JSON_FILE)
    image_results = validate_image(IMAGE_FILE, JSON_FILE)

    all_results = json_results + image_results
    passed = sum(1 for r in all_results if r["passed"])

    print(f"\nResults: {passed}/{len(all_results)} checks passed\n")
    for r in all_results:
        print(f"  [{r['layer']:5}] {status_icon(r['passed'])}  {r['check']}")
        if not r["passed"]:
            print(f"          ↳ {r['detail']}")

    # ── Write HTML report ──────────────────────────────────────
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(OUTPUT_DIR, "eval_report.html")
    html = build_report(json_results, image_results, JSON_FILE, IMAGE_FILE)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    abs_path = os.path.abspath(report_path)
    print(f"\n📄 Report saved → {abs_path}")
    webbrowser.open(f"file:///{abs_path}")
    print("   (Report opened in your browser)")
    print("=" * 55)


if __name__ == "__main__":
    main()
