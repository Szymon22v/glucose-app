import json
import sys
from pathlib import Path

from logic import evaluate, save_glucose_report_html, save_output_json


def load_input_json(input_path: str) -> dict:
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Nie znaleziono pliku: {input_path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_glucose_from_json(data: dict):
    """
    Szuka badania glukozy w polu result.
    Oczekiwany format pojedynczego rekordu, np.:
    {
      "code": "GLU",
      "value": 168,
      "unit": "mg/dL",
      "refLow": 70,
      "refHigh": 99
    }
    """
    results = data.get("result", [])

    for item in results:
        code = str(item.get("code", "")).upper()
        if code == "GLU":
            value = item.get("value")
            unit = item.get("unit", "mg/dL")

            if value is None:
                raise ValueError('Rekord GLU nie zawiera pola "value".')

            return float(value), unit

    raise ValueError('Nie znaleziono badania o kodzie "GLU" w polu result.')


def main():
    if len(sys.argv) < 2:
        print("Użycie: python json_runner.py input.json")
        sys.exit(1)

    input_path = sys.argv[1]

    try:
        data = load_input_json(input_path)
        value, unit = extract_glucose_from_json(data)

        result = evaluate(value, unit)

        report_path = save_glucose_report_html(
            result,
            source_name=Path(input_path).name,
            output_dir="reports"
        )

        json_path = save_output_json(
            result,
            source_name=Path(input_path).name,
            output_dir="outputs"
        )

        cli_output = {
            "source_file": Path(input_path).name,
            "report_path": report_path,
            "json_path": json_path,
            "result": result
        }

        print(json.dumps(cli_output, ensure_ascii=False, indent=2))

    except Exception as exc:
        error_output = {"error": str(exc)}
        print(json.dumps(error_output, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()