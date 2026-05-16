import json
from pathlib import Path

from logic import extract_text_from_file, find_glucose, evaluate, save_glucose_report_html


TEST_DIR = Path("test_inputs/pdf")
OUTPUT_PATH = Path("outputs/summaries/pdf_test_summary.json")


def expected_flag_from_filename(filename: str):
    """
    Returns expected H/L/N flag based on the PDF filename.
    This is used only for test files.
    """
    name = filename.lower()

    # Low glucose
    if (
        "ponizej" in name
        or "poniżej" in name
        or "niska" in name
        or "nisko" in name
        or "low" in name
    ):
        return "L"

    # High glucose
    if (
        "powyzej" in name
        or "powyżej" in name
        or "wysoka" in name
        or "wysoko" in name
        or "high" in name
    ):
        return "H"

    # Normal glucose
    if (
        "normie" in name
        or "norma" in name
        or "normal" in name
        or "w_normie" in name
    ):
        return "N"

    return None


def main():
    pdf_files = sorted(TEST_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in test_inputs/pdf.")
        return

    total = 0
    correct = 0
    rows = []

    print("\nPDF TEST RESULTS")
    print("-" * 130)
    print(
        f"{'File':60} "
        f"{'Value':>8} "
        f"{'Unit':>8} "
        f"{'Expected':>10} "
        f"{'Predicted':>10} "
        f"{'Correct':>10} "
        f"{'Report':>20}"
    )
    print("-" * 130)

    for pdf_file in pdf_files:
        expected_flag = expected_flag_from_filename(pdf_file.name)

        file_bytes = pdf_file.read_bytes()
        text = extract_text_from_file(file_bytes, pdf_file.name)

        value, unit, ref_low, ref_high = find_glucose(text)
        result = evaluate(value, unit, ref_low, ref_high)

        report_path = save_glucose_report_html(
            result,
            source_name=pdf_file.name,
            output_dir="reports/pdf"
        )

        value, unit, ref_low, ref_high= find_glucose(text)
        result = evaluate(value, unit, ref_low, ref_high)


        predicted_flag = result.get("flag")
        is_correct = expected_flag == predicted_flag if expected_flag else None

        total += 1

        if is_correct:
            correct += 1

        row = {
            "file": pdf_file.name,
            "value": result.get("value"),
            "unit": result.get("unit"),
            "value_mgdl": result.get("value_mgdl"),
            "expected_flag": expected_flag,
            "predicted_flag": predicted_flag,
            "correct": is_correct,
            "validation_errors": result.get("validation_errors", []),
            "report_path": str(report_path),
        }

        rows.append(row)

        print(
            f"{pdf_file.name:60} "
            f"{str(row['value']):>8} "
            f"{str(row['unit']):>8} "
            f"{str(row['expected_flag']):>10} "
            f"{str(row['predicted_flag']):>10} "
            f"{str(row['correct']):>10} "
            f"{str(row['report_path']):>20}"
        )

    print("-" * 130)

    accuracy = correct / total * 100 if total else 0

    print(f"Correct predictions: {correct}/{total}")
    print(f"Accuracy: {accuracy:.2f}%")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "test_set": "PDF",
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