import json
from pathlib import Path

from logic import (
    extract_text_from_file,
    find_glucose,
    evaluate,
    save_glucose_report_html,
)


TEST_DIR = Path("test_inputs/images")
OUTPUT_PATH = Path("outputs/summaries/image_test_summary.json")


EXPECTED_FLAGS = {
    "pacjent_01_glukoza_w_normie.jpg": "N",
    "pacjent_02_glukoza_ponizej_normy.jpg": "L",
    "pacjent_03_glukoza_skrajnie_niska.jpg": "L",
    "pacjent_04_glukoza_powyzej_normy.jpg": "H",
    "pacjent_05_glukoza_skrajnie_wysoka.jpg": "H",
    "pacjent_06_glu_w_normie.jpg": "N",
    "pacjent_07_glucose_mmol_normal.jpg": "N",
    "pacjent_08_glucose_mmol_high.jpg": "H",
}


def expected_flag_from_filename(filename: str):
    name = filename.lower()

    if name in EXPECTED_FLAGS:
        return EXPECTED_FLAGS[name]

    if "low" in name or "ponizej" in name or "poniżej" in name or "niska" in name:
        return "L"

    if "high" in name or "powyzej" in name or "powyżej" in name or "wysoka" in name:
        return "H"

    if "normal" in name or "normie" in name or "norma" in name or "na_czczo" in name:
        return "N"

    return None


def analyze_image(image_file: Path):
    file_bytes = image_file.read_bytes()
    text = extract_text_from_file(file_bytes, image_file.name)

    found = find_glucose(text)

    if len(found) == 4:
        value, unit, ref_low, ref_high = found
    else:
        value, unit = found
        ref_low, ref_high = None, None

    try:
        result = evaluate(value, unit, ref_low, ref_high)
    except TypeError:
        result = evaluate(value, unit)

    return text, result


def main():
    image_files = sorted(
        list(TEST_DIR.glob("*.jpg")) +
        list(TEST_DIR.glob("*.jpeg")) +
        list(TEST_DIR.glob("*.png"))
    )

    if not image_files:
        print("No image files found in test_inputs/images.")
        return

    total = 0
    correct = 0
    rows = []

    print("\nIMAGE TEST RESULTS")
    print("-" * 145)
    print(
        f"{'File':55} "
        f"{'Value':>8} "
        f"{'Unit':>8} "
        f"{'mg/dL':>8} "
        f"{'Expected':>10} "
        f"{'Predicted':>10} "
        f"{'Correct':>10} "
        f"{'Report':>20}"
    )
    print("-" * 145)

    for image_file in image_files:
        expected_flag = expected_flag_from_filename(image_file.name)

        try:
            ocr_text, result = analyze_image(image_file)

            predicted_flag = result.get("flag")
            is_correct = expected_flag == predicted_flag if expected_flag else None

            report_path = save_glucose_report_html(
                result,
                source_name=image_file.name,
                output_dir="reports/images"
            )

            total += 1
            if is_correct:
                correct += 1

            row = {
                "file": image_file.name,
                "value": result.get("value"),
                "unit": result.get("unit"),
                "value_mgdl": result.get("value_mgdl"),
                "expected_flag": expected_flag,
                "predicted_flag": predicted_flag,
                "correct": is_correct,
                "validation_errors": result.get("validation_errors", []),
                "ocr_text": ocr_text,
                "report_path": str(report_path),
            }

        except Exception as error:
            total += 1
            row = {
                "file": image_file.name,
                "value": None,
                "unit": None,
                "value_mgdl": None,
                "expected_flag": expected_flag,
                "predicted_flag": None,
                "correct": False,
                "validation_errors": [str(error)],
                "ocr_text": "",
                "report_path": None,
            }

        rows.append(row)

        print(
            f"{row['file']:55} "
            f"{str(row['value']):>8} "
            f"{str(row['unit']):>8} "
            f"{str(row['value_mgdl']):>8} "
            f"{str(row['expected_flag']):>10} "
            f"{str(row['predicted_flag']):>10} "
            f"{str(row['correct']):>10} "
            f"{str(row['report_path']):>20}"
        )

    print("-" * 145)

    accuracy = correct / total * 100 if total else 0

    print(f"Correct predictions: {correct}/{total}")
    print(f"Accuracy: {accuracy:.2f}%")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "test_set": "images",
        "total_tests": total,
        "correct_predictions": correct,
        "accuracy_percent": round(accuracy, 2),
        "results": rows,
    }

    OUTPUT_PATH.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\nTest summary saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()