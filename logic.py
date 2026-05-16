import pdfplumber
import re
import io
from pathlib import Path
from datetime import datetime
import html
import json

import fitz  # PyMuPDF
import easyocr
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter


# ─── Stałe referencyjne ───────────────────────────────────────────────────────
GLUCOSE_REF_LOW = 70     # mg/dL
GLUCOSE_REF_HIGH = 99    # mg/dL


# ─── EasyOCR reader ───────────────────────────────────────────────────────────
_OCR_READER = None


def get_ocr_reader():
    """
    Creates and returns EasyOCR reader.
    Polish and English languages are used.
    GPU is disabled to make the app work on normal computers.
    """
    global _OCR_READER

    if _OCR_READER is None:
        _OCR_READER = easyocr.Reader(["pl", "en"], gpu=False)

    return _OCR_READER


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Prepares image for OCR.
    The image is corrected, enlarged, sharpened and contrast-enhanced.
    This improves recognition of small text in medical reports.
    """
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")

    # Enlarge small images before OCR.
    width, height = image.size
    scale = 2

    if max(width, height) < 2500:
        image = image.resize((width * scale, height * scale), Image.Resampling.LANCZOS)

    # Improve contrast and sharpness.
    image = ImageOps.autocontrast(image)
    image = ImageEnhance.Contrast(image).enhance(1.8)
    image = ImageEnhance.Sharpness(image).enhance(2.0)
    image = image.filter(ImageFilter.SHARPEN)

    return image


def ocr_image_to_text(image: Image.Image) -> str:
    """
    Reads text from a PIL image using EasyOCR.
    Parameters are adjusted for smaller text in laboratory reports.
    """
    image = preprocess_image_for_ocr(image)
    image_array = np.array(image)

    reader = get_ocr_reader()

    results = reader.readtext(
        image_array,
        detail=1,
        paragraph=False,
        decoder="beamsearch",
        beamWidth=5,
        mag_ratio=2.0,
        canvas_size=3500,
        text_threshold=0.5,
        low_text=0.3,
        link_threshold=0.3,
        contrast_ths=0.1,
        adjust_contrast=0.7,
        width_ths=1.0,
    )

    lines = []

    for bbox, text, confidence in results:
        # Ignore very weak detections.
        if confidence < 0.20:
            continue

        y_center = sum(point[1] for point in bbox) / 4
        x_min = min(point[0] for point in bbox)

        lines.append((y_center, x_min, text))

    if not lines:
        return ""

    # Sort text from top to bottom and left to right.
    lines.sort(key=lambda item: (item[0], item[1]))

    grouped_lines = []
    current_line = []
    current_y = lines[0][0]

    for y, x, text in lines:
        if abs(y - current_y) > 25:
            grouped_lines.append(" ".join(current_line))
            current_line = [text]
            current_y = y
        else:
            current_line.append(text)

    if current_line:
        grouped_lines.append(" ".join(current_line))

    return "\n".join(grouped_lines)


def extract_text_from_image(file_bytes: bytes) -> str:
    """
    Extracts text from image file using OCR.
    Supported formats: PNG, JPG, JPEG.
    """
    image = Image.open(io.BytesIO(file_bytes))
    return ocr_image_to_text(image)


def extract_text_from_scanned_pdf(file_bytes: bytes, dpi: int = 400) -> str:
    """
    Converts each page of scanned PDF into an image
    and extracts text using EasyOCR.
    """
    pages_text = []

    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            image_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(image_bytes))

            page_text = ocr_image_to_text(image)
            pages_text.append(page_text)

    return "\n".join(pages_text)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts text from PDF.
    First, it tries normal text extraction with pdfplumber.
    If the PDF has no selectable text, OCR is used.
    """
    text = ""

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception:
        text = ""

    text = text.strip()

    if len(text) > 20:
        return text

    return extract_text_from_scanned_pdf(file_bytes)


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """
    Extracts text from PDF or image file.
    Text PDF files are handled by pdfplumber.
    Scanned PDF files and images are handled by EasyOCR.
    """
    filename = filename.lower()

    if filename.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)

    if filename.endswith((".png", ".jpg", ".jpeg")):
        return extract_text_from_image(file_bytes)

    raise ValueError("Nieobsługiwany format pliku. Wgraj PDF, PNG, JPG lub JPEG.")


def find_glucose(text: str):
    """
    Searches for glucose value and unit in extracted text.
    The function looks for a line containing 'glukoza' or 'glucose'.
    """
    normalized = re.sub(r"[ \t]+", " ", text)

    for line in normalized.splitlines():
        line_lower = line.lower()

        if "glukoza" not in line_lower and "glucose" not in line_lower:
            continue

        numbers = re.findall(r"\b(\d{1,3}(?:[.,]\d+)?)\b", line)

        if numbers:
            value_str = numbers[0].replace(",", ".")
            value = float(value_str)

            if 20 <= value <= 600:
                unit = "mmol/L" if "mmol" in line_lower else "mg/dL"
                return value, unit

    return None, None


def evaluate(value: float, unit: str) -> dict:
    """
    Evaluates glucose value against the reference range.
    The comparison is performed in mg/dL.
    """
    low = GLUCOSE_REF_LOW
    high = GLUCOSE_REF_HIGH

    if unit == "mmol/L":
        value_mgdl = value * 18.018
    else:
        value_mgdl = value

    if value_mgdl < low:
        status = "low"
        label = "Za niska"
        advice = (
            "Twój poziom glukozy jest poniżej normy (hipoglikemia). "
            "Skonsultuj się z lekarzem."
        )
    elif value_mgdl > high:
        status = "high"
        label = "Za wysoka"
        advice = (
            "Twój poziom glukozy jest powyżej normy. "
            "Może to wskazywać na stan przedcukrzycowy lub cukrzycę. "
            "Skonsultuj się z lekarzem."
        )
    else:
        status = "normal"
        label = "W normie"
        advice = "Twój poziom glukozy jest prawidłowy. Tak trzymaj!"

    return {
        "value": value,
        "value_mgdl": round(value_mgdl, 1),
        "unit": unit,
        "status": status,
        "label": label,
        "advice": advice,
        "ref_low": low,
        "ref_high": high,
    }


def build_glucose_report_html(result: dict, source_name: str = "input.pdf") -> str:
    value = html.escape(str(result.get("value", "")))
    unit = html.escape(str(result.get("unit", "")))
    label = html.escape(str(result.get("label", "")))
    advice = html.escape(str(result.get("advice", "")))
    status = result.get("status", "normal")
    ref_low = html.escape(str(result.get("ref_low", "")))
    ref_high = html.escape(str(result.get("ref_high", "")))
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source_name = html.escape(source_name)

    status_colors = {
        "normal": ("#ecfdf5", "#12b76a", "#a6f4c5"),
        "high": ("#fef2f2", "#ef4444", "#fecaca"),
        "low": ("#fffbeb", "#f59e0b", "#fde68a"),
    }

    bg, text_color, border = status_colors.get(
        status,
        ("#f8fafc", "#1f2937", "#cbd5e1")
    )

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Raport glukozy</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      background: #f3f4f6;
      color: #111827;
      margin: 0;
      padding: 32px;
    }}
    .container {{
      max-width: 820px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #e5e7eb;
      border-radius: 16px;
      overflow: hidden;
    }}
    .header {{
      padding: 24px 28px;
      border-bottom: 1px solid #e5e7eb;
    }}
    .header h1 {{
      margin: 0 0 8px 0;
      font-size: 28px;
    }}
    .meta {{
      color: #6b7280;
      font-size: 14px;
    }}
    .content {{
      padding: 28px;
    }}
    .value {{
      font-size: 56px;
      font-weight: bold;
      line-height: 1;
      margin-bottom: 8px;
    }}
    .unit {{
      color: #6b7280;
      margin-bottom: 16px;
    }}
    .badge {{
      display: inline-block;
      padding: 8px 16px;
      border-radius: 999px;
      background: {bg};
      color: {text_color};
      border: 1px solid {border};
      font-weight: bold;
      margin-bottom: 24px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      margin-bottom: 24px;
    }}
    th, td {{
      text-align: left;
      padding: 12px;
      border-bottom: 1px solid #e5e7eb;
    }}
    th {{
      background: #f9fafb;
    }}
    .advice {{
      background: {bg};
      border: 1px solid {border};
      border-radius: 12px;
      padding: 16px;
    }}
    .footer {{
      padding: 20px 28px;
      border-top: 1px solid #e5e7eb;
      color: #6b7280;
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Raport analizy glukozy</h1>
      <div class="meta">Plik źródłowy: {source_name}</div>
      <div class="meta">Data wygenerowania: {generated_at}</div>
    </div>

    <div class="content">
      <div class="value">{value}</div>
      <div class="unit">{unit}</div>
      <div class="badge">{label}</div>

      <table>
        <thead>
          <tr>
            <th>Badanie</th>
            <th>Wynik</th>
            <th>Jednostka</th>
            <th>Zakres referencyjny</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Glukoza</td>
            <td>{value}</td>
            <td>{unit}</td>
            <td>{ref_low} - {ref_high}</td>
            <td>{label}</td>
          </tr>
        </tbody>
      </table>

      <div class="advice">
        <strong>Interpretacja:</strong><br>
        {advice}
      </div>
    </div>

    <div class="footer">
      Raport wygenerowany automatycznie przez aplikację GlucoScan.
    </div>
  </div>
</body>
</html>
"""


def save_glucose_report_html(
    result: dict,
    source_name: str = "input.pdf",
    output_dir: str = "reports"
) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    safe_name = Path(source_name).stem.replace(" ", "_")
    output_path = Path(output_dir) / f"{safe_name}_report.html"

    html_content = build_glucose_report_html(result, source_name=source_name)
    output_path.write_text(html_content, encoding="utf-8")

    return str(output_path)


def save_output_json(
    result: dict,
    source_name: str = "input.pdf",
    output_dir: str = "outputs"
) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    safe_name = Path(source_name).stem.replace(" ", "_")
    output_path = Path(output_dir) / f"{safe_name}_output.json"

    output_data = {
        "source_file": source_name,
        "test": "GLU",
        "value": result.get("value"),
        "unit": result.get("unit"),
        "value_mgdl": result.get("value_mgdl"),
        "status": result.get("status"),
        "label": result.get("label"),
        "advice": result.get("advice"),
        "ref_low": result.get("ref_low"),
        "ref_high": result.get("ref_high"),
    }

    output_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return str(output_path)