from flask import Flask, request, jsonify, render_template
from logic import extract_text_from_pdf, find_glucose, evaluate, save_glucose_report_html, save_output_json

app = Flask(__name__)

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
        # DODANE
        report_path = save_glucose_report_html(result, source_name=file.filename)
        json_path = save_output_json(result, source_name=file.filename)

        result["report_path"] = report_path
        result["json_path"] = json_path

        return jsonify(result)

    except Exception as exc:
        return jsonify({'error': f'Błąd przetwarzania: {str(exc)}'}), 500


# ─── Start ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, port=5000)
