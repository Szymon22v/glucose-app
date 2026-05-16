import pdfplumber
import re
import io
from pathlib import Path
from datetime import datetime
import html
import json

import fitz  
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

def extract_reference_range(fragment: str):
    """
    Tries to extract reference range from text fragment.
    Supported examples:
    70 - 99
    3,9 - 6,1
    70–99
    """
    range_match = re.search(
        r"(\d{1,3}(?:[.,]\d+)?)\s*[-–—_=]\s*(\d{1,3}(?:[.,]\d+)?)",
        fragment
    )
    if not range_match:
        return None, None

    ref_low = float(range_match.group(1).replace(",", "."))
    ref_high = float(range_match.group(2).replace(",", "."))

    return ref_low, ref_high

def find_glucose(text: str):
    """
    Searches for glucose value, unit and reference range in extracted text.

    Returns:
    - value
    - unit
    - ref_low
    - ref_high
    """
    if not text:
        return None, None, None, None

    normalized = text.replace("\t", " ")
    normalized = re.sub(r"[ ]{2,}", " ", normalized)

    lines = [line.strip() for line in normalized.splitlines() if line.strip()]

    glucose_keywords_pattern = r"\b(glukoza|glucose|glu|glc)\b"
    unit_pattern = r"(mg\s*/?\s*d[l1i]|mgdl|mgldl|mg\s*l\s*d[l1i]|mmol\s*/?\s*l|mmoll|mmolll)"

    def parse_number(number_text):
        return float(number_text.replace(",", "."))

    def normalize_unit(unit_raw):
        unit_clean = unit_raw.lower().replace(" ", "")
        unit_clean = unit_clean.replace("mgldl", "mg/dl")

        if "mmol" in unit_clean:
            return "mmol/L"

        return "mg/dL"

    def detect_unit(fragment):
        fragment_lower = fragment.lower().replace(" ", "")

        if "mmol/l" in fragment_lower or "mmoll" in fragment_lower:
            return "mmol/L"

        if (
            "mg/dl" in fragment_lower
            or "mgdl" in fragment_lower
            or "mgldl" in fragment_lower
            or "mg/d1" in fragment_lower
        ):
            return "mg/dL"

        return "mg/dL"

    def is_valid_value(value, unit):
        if unit == "mmol/L":
            return 1 <= value <= 35

        return 20 <= value <= 600

    def extract_reference_range(fragment):
        """
        Extracts reference range like:
        70 - 99
        70–99
        70 — 99
        3.9 - 5.5
        3,9 - 5,5
        """
        range_match = re.search(
            r"(\d{1,3}(?:[.,]\d+)?)\s*[-–—_=]\s*(\d{1,3}(?:[.,]\d+)?)",
            fragment
        )

        if range_match:
            ref_low = parse_number(range_match.group(1))
            ref_high = parse_number(range_match.group(2))

            if ref_low < ref_high:
                return ref_low, ref_high

        return None, None

    def remove_reference_ranges(fragment):
        """
        Removes reference ranges before looking for the actual glucose value.
        This prevents 70 from 70-99 from being detected as the result.
        """
        return re.sub(
            r"\b\d{1,3}(?:[.,]\d+)?\s*[-–—_=]\s*\d{1,3}(?:[.,]\d+)?\b",
            " ",
            fragment
        )

    def glucose_priority(fragment):
        fragment_lower = fragment.lower()

        if "ogtt" in fragment_lower or "120" in fragment_lower or "po 120" in fragment_lower:
            return 10

        if "surowicy" in fragment_lower or "osoczu" in fragment_lower or "(glu)" in fragment_lower:
            return 100

        if "na czczo" in fragment_lower or "fasting" in fragment_lower:
            return 90

        if "glukoza" in fragment_lower or "glucose" in fragment_lower or "glu" in fragment_lower:
            return 70

        return 0

    def extract_from_fragment(fragment):
        fragment_lower = fragment.lower()

        keyword_match = re.search(glucose_keywords_pattern, fragment_lower)

        if not keyword_match:
            return None

        start = max(0, keyword_match.start() - 120)
        end = min(len(fragment), keyword_match.end() + 260)
        searchable = fragment[start:end]

        ref_low, ref_high = extract_reference_range(searchable)


        searchable_without_ranges = remove_reference_ranges(searchable)
        searchable_without_ranges_lower = searchable_without_ranges.lower()


        value_unit_match = re.search(
            rf"(\d{{1,3}}(?:[.,]\d+)?)\s*{unit_pattern}",
            searchable_without_ranges_lower
        )

        if value_unit_match:
            value = parse_number(value_unit_match.group(1))
            unit_raw = value_unit_match.group(2)
            unit = normalize_unit(unit_raw)


            if is_valid_value(value, unit):

                ref_low, ref_high = extract_reference_range(searchable)
                return {
                    "value": value,
                    "unit": unit,
                    "ref_low": ref_low,
                    "ref_high": ref_high,
                    "priority": glucose_priority(fragment),
                    "line": fragment,
                }

        unit_value_match = re.search(
            rf"{unit_pattern}\s*(\d{{1,3}}(?:[.,]\d+)?)",
            searchable_without_ranges_lower
        )

        if unit_value_match:
            unit_raw = unit_value_match.group(1)
            value = parse_number(unit_value_match.group(2))
            unit = normalize_unit(unit_raw)

            if is_valid_value(value, unit):

                ref_low, ref_high = extract_reference_range(searchable)
                return {
                    "value": value,
                    "unit": unit,
                    "ref_low": ref_low,
                    "ref_high": ref_high,
                    "priority": glucose_priority(fragment),
                    "line": fragment,
                }

        unit = detect_unit(searchable_without_ranges)

        for match in re.finditer(r"\b(\d{1,3}(?:[.,]\d+)?)\b", searchable_without_ranges):
            number_text = match.group(1)
            value = parse_number(number_text)

            if is_valid_value(value, unit):
                ref_low, ref_high = extract_reference_range(searchable)
                return {
                    "value": value,
                    "unit": unit,
                    "ref_low": ref_low,
                    "ref_high": ref_high,
                    "priority": glucose_priority(fragment),
                    "line": fragment,
                }

        return None

    candidates = []

    for i, line in enumerate(lines):
        context = " ".join(lines[i:i + 8])

        if not re.search(glucose_keywords_pattern, context.lower()):
            continue

        candidate = extract_from_fragment(context)

        if candidate is not None:
            candidates.append(candidate)

    if not candidates:
        candidate = extract_from_fragment(normalized)

        if candidate is not None:
            candidates.append(candidate)

    if not candidates:
        return None, None, None, None

    candidates.sort(key=lambda item: item["priority"], reverse=True)
    best = candidates[0]


    return best["value"], best["unit"], best["ref_low"], best["ref_high"]


def evaluate(value: float, unit: str, ref_low=None, ref_high=None) -> dict:
    """
    Evaluates glucose value against the reference range.
    The comparison is performed in mg/dL.

    The function assigns the H/L/N flag:
    - L: below reference range
    - N: within reference range
    - H: above reference range

    It also returns validation_errors, which contains detected
    problems related to the extracted value, unit or reference range.
    """
    validation_errors = []

    # low = GLUCOSE_REF_LOW
    # high = GLUCOSE_REF_HIGH

    # Domyślny zakres tylko jako fallback
    default_low = GLUCOSE_REF_LOW
    default_high = GLUCOSE_REF_HIGH

    validation_errors = []

    # Validate value
    try:
        value = float(value)
    except (TypeError, ValueError):
        validation_errors.append("Nieprawidłowa lub nieodczytana wartość glukozy.")
        value = 0.0

    # Validate and normalize unit
    if unit is None or str(unit).strip() == "":
        validation_errors.append("Nie odczytano jednostki wyniku, przyjęto domyślnie mg/dL.")
        unit = "mg/dL"

    unit_clean = str(unit).strip().lower().replace(" ", "")

    if unit_clean in ["mg/dl", "mg/dl."]:
        unit = "mg/dL"
    elif unit_clean in ["mmol/l", "mmol/l."]:
        unit = "mmol/L"
    else:
        validation_errors.append(
            f"Nieobsługiwana jednostka wyniku: {unit}. Przyjęto domyślnie mg/dL."
        )
        unit = "mg/dL"

    # Referencyjny zakres wejściowy
    try:
        low = float(ref_low) if ref_low is not None else None
    except (TypeError, ValueError):
        low = None
        validation_errors.append("Nieprawidłowa dolna granica zakresu referencyjnego.")

    try:
        high = float(ref_high) if ref_high is not None else None
    except (TypeError, ValueError):
        high = None
        validation_errors.append("Nieprawidłowa górna granica zakresu referencyjnego.")

    # Fallback do stałych, jeśli zakres nie został odczytany
    if low is None:
        low = default_low
        validation_errors.append("Nie odczytano dolnej granicy zakresu, użyto wartości domyślnej.")

    if high is None:
        high = default_high
        validation_errors.append("Nie odczytano górnej granicy zakresu, użyto wartości domyślnej.")


    # Convert to mg/dL for comparison
    if unit == "mmol/L":
        value_mgdl = value * 18.018
    else:
        value_mgdl = value

    # Validate realistic range
    if value_mgdl < 20 or value_mgdl > 600:
        validation_errors.append(
            "Odczytana wartość glukozy znajduje się poza typowym zakresem kontrolnym 20–600 mg/dL."
        )

    # Evaluate result
    if value_mgdl < low:
        status = "low"
        flag = "L"
        label = "Za niska"
        advice = (
            "Twój poziom glukozy jest poniżej normy (hipoglikemia). "
            "Skonsultuj się z lekarzem."
        )
    elif value_mgdl > high:
        status = "high"
        flag = "H"
        label = "Za wysoka"
        advice = (
            "Twój poziom glukozy jest powyżej normy. "
            "Może to wskazywać na stan przedcukrzycowy lub cukrzycę. "
            "Skonsultuj się z lekarzem."
        )
    else:
        status = "normal"
        flag = "N"
        label = "W normie"
        advice = "Twój poziom glukozy jest prawidłowy. Tak trzymaj!"

    return {
        "value": round(value, 2),
        "value_mgdl": round(value_mgdl, 1),
        "unit": unit,
        "status": status,
        "flag": flag,
        "label": label,
        "advice": advice,
        "ref_low": low,
        "ref_high": high,
        "validation_errors": validation_errors,
    }


def build_glucose_report_html(result: dict, source_name: str = "input.pdf") -> str:
    value = html.escape(str(result.get("value", "")))
    unit = html.escape(str(result.get("unit", "")))
    label = html.escape(str(result.get("label", "")))
    flag = html.escape(str(result.get("flag", "")))
    advice = html.escape(str(result.get("advice", "")))
    status = result.get("status", "normal")
    ref_low = html.escape(str(result.get("ref_low", "")))
    ref_high = html.escape(str(result.get("ref_high", "")))
    raw_value = result.get("value", "")
    raw_unit = result.get("unit", "")
    raw_value_mgdl = result.get("value_mgdl", "")
    if raw_unit == "mmol/L" and raw_value_mgdl not in ("", None):
        converted_value = f"{float(raw_value_mgdl):.1f}"
        display_value = html.escape(f"{raw_value} mmol/L ≈ {converted_value} mg/dL")
        display_unit = ""
        value_class = "value value-small"
    else:
        display_value = value
        display_unit = unit
        value_class = "value"

    validation_errors = result.get("validation_errors", [])
    if validation_errors:
        validation_errors_html = "<ul>" + "".join(
            f"<li>{html.escape(str(error))}</li>" for error in validation_errors
        ) + "</ul>"
    else:
        validation_errors_html = "<p>Brak błędów walidacji.</p>"
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
    .value-small {{
        font-size: 28px;
        line-height: 1.25;
        max-width: 100%;
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
    .validation {{
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 16px;
        margin-top: 16px;
    }}
    .validation ul {{
        margin: 8px 0 0 20px;
        padding: 0;
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
      <div class="{value_class}">{display_value}</div>
      <div class="unit">{display_unit}</div>
      <div class="badge">Flaga: {flag} — {label}</div>

      <table>
        <thead>
          <tr>
            <th>Badanie</th>
            <th>Wynik</th>
            <th>Jednostka</th>
            <th>Zakres referencyjny</th>
            <th>Flaga</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Glukoza</td>
            <td>{value}</td>
            <td>{unit}</td>
            <td>{ref_low} - {ref_high}</td>
            <td>{flag}</td>
            <td>{label}</td>
          </tr>
        </tbody>
      </table>

      <div class="advice">
        <strong>Interpretacja:</strong><br>
        {advice}
      </div>
      <div class="validation">
        <strong>Walidacja danych:</strong>
        {validation_errors_html}
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
        "flag": result.get("flag"),
        "label": result.get("label"),
        "advice": result.get("advice"),
        "ref_low": result.get("ref_low"),
        "ref_high": result.get("ref_high"),
        "validation_errors": result.get("validation_errors", []),
    }

    output_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return str(output_path)