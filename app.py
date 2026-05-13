from flask import Flask, request, jsonify, render_template
import pdfplumber
import re
import io

app = Flask(__name__)

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


# ─── Endpointy ────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    if 'pdf' not in request.files:
        return jsonify({'error': 'Nie przesłano pliku PDF.'}), 400

    file = request.files['pdf']

    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Proszę wybrać plik PDF.'}), 400

    try:
        file_bytes = file.read()
        text       = extract_text_from_pdf(file_bytes)

        if not text.strip():
            return jsonify({'error': 'Nie udało się odczytać tekstu z PDF.'}), 422

        value, unit = find_glucose(text)

        if value is None:
            return jsonify({
                'error': 'Nie znaleziono parametru "Glukoza" w tym dokumencie.'
            }), 404

        result = evaluate(value, unit)
        return jsonify(result)

    except Exception as exc:
        return jsonify({'error': f'Błąd przetwarzania: {str(exc)}'}), 500


# ─── Start ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, port=5000)
