import pdfplumber
import re
import io
from pathlib import Path
from datetime import datetime
import html
import json

# ─── Stałe referencyjne ───────────────────────────────────────────────────────
GLUCOSE_REF_LOW  = 70    # mg/dL
GLUCOSE_REF_HIGH = 99    # mg/dL


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Zwraca cały tekst ze wszystkich stron PDF-a."""
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def find_glucose(text: str):
    """
    Szuka linii zawierającej 'glukoza' i wyciąga wartość numeryczną.
    Obsługuje różne formaty tabel z wyników laboratoryjnych.

    Przykładowe linie:
      Glukoza 168 mg/dL 70 - 99
      Glukoza 127 mg/dL 70 - 99
      Glukoza 92 mg/dL 70 - 99
    """

    # Normalizacja – zamień tabulatory / wielokrotne spacje na pojedyncze
    normalized = re.sub(r'[ \t]+', ' ', text)

    # Szukamy linii z 'glukoza' (case-insensitive)
    for line in normalized.splitlines():
        if re.search(r'glukoza', line, re.IGNORECASE):
            # Wyciągnij pierwszą liczbę dziesiętną z tej linii
            # (może być z przecinkiem lub kropką jako separator dziesiętny)
            numbers = re.findall(r'\b(\d{2,3}(?:[.,]\d+)?)\b', line)
            if numbers:
                value_str = numbers[0].replace(',', '.')
                value = float(value_str)
                # Prosta sanitacja – glukoza w mg/dL mieści się w 20–600
                if 20 <= value <= 600:
                    # Sprawdź czy w linii jest mmol/L
                    unit = 'mmol/L' if 'mmol' in line.lower() else 'mg/dL'
                    return value, unit

    return None, None

def evaluate(value: float, unit: str) -> dict:
    """Ocenia wartość glukozy względem zakresu referencyjnego."""
    low  = GLUCOSE_REF_LOW
    high = GLUCOSE_REF_HIGH

    # Przelicz mmol/L → mg/dL jeśli potrzeba
    if unit == 'mmol/L':
        value_mgdl = value * 18.018
    else:
        value_mgdl = value

    if value_mgdl < low:
        status  = 'low'
        label   = 'Za niska'
        advice  = ('Twój poziom glukozy jest poniżej normy (hipoglikemia). '
                   'Skonsultuj się z lekarzem.')
    elif value_mgdl > high:
        status  = 'high'
        label   = 'Za wysoka'
        advice  = ('Twój poziom glukozy jest powyżej normy. '
                   'Może to wskazywać na stan przedcukrzycowy lub cukrzycę. '
                   'Skonsultuj się z lekarzem.')
    else:
        status  = 'normal'
        label   = 'W normie'
        advice  = 'Twój poziom glukozy jest prawidłowy. Tak trzymaj!'

    return {
        'value':       value,
        'value_mgdl':  round(value_mgdl, 1),
        'unit':        unit,
        'status':      status,
        'label':       label,
        'advice':      advice,
        'ref_low':     low,
        'ref_high':    high,
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

    bg, text_color, border = status_colors.get(status, ("#f8fafc", "#1f2937", "#cbd5e1"))

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


def save_glucose_report_html(result: dict, source_name: str = "input.pdf", output_dir: str = "reports") -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    safe_name = Path(source_name).stem.replace(" ", "_")
    output_path = Path(output_dir) / f"{safe_name}_report.html"

    html_content = build_glucose_report_html(result, source_name=source_name)
    output_path.write_text(html_content, encoding="utf-8")

    return str(output_path)


def save_output_json(result: dict, source_name: str = "input.pdf", output_dir: str = "outputs") -> str:
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