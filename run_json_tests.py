import json
from pathlib import Path

from json_runner import load_input_json, extract_glucose_from_json
from logic import evaluate


TEST_DIR = Path("test_inputs/json")


def get_expected_flag(data):
    results = data.get("result", [])

    for item in results:
        if str(item.get("code", "")).upper() == "GLU":
            return item.get("expectedFlag")

    return None


def main():
    json_files = sorted(TEST_DIR.glob("*.json"))

    if not json_files:
        print("No JSON test files found.")
        return

    total = 0
    correct = 0
    rows = []

    for json_file in json_files:
        data = load_input_json(json_file)

        expected_flag = get_expected_flag(data)

        value, unit = extract_glucose_from_json(data)
        result = evaluate(value, unit)

        predicted_flag = result.get("flag")

        is_correct = expected_flag == predicted_flag

        total += 1
        if is_correct:
            correct += 1

        rows.append({
            "file": json_file.name,
            "value": result.get("value"),
            "unit": result.get("unit"),
            "value_mgdl": result.get("value_mgdl"),
            "expected_flag": expected_flag,
            "predicted_flag": predicted_flag,
            "correct": is_correct
        })

    accuracy = correct / total * 100

    print("\nJSON TEST RESULTS")
    print("-" * 90)
    print(f"{'File':30} {'Value':>8} {'Unit':>8} {'Expected':>10} {'Predicted':>10} {'Correct':>10}")
    print("-" * 90)

    for row in rows:
        print(
            f"{row['file']:30} "
            f"{str(row['value']):>8} "
            f"{row['unit']:>8} "
            f"{row['expected_flag']:>10} "
            f"{row['predicted_flag']:>10} "
            f"{str(row['correct']):>10}"
        )

    print("-" * 90)
    print(f"Correct predictions: {correct}/{total}")
    print(f"Accuracy: {accuracy:.2f}%")

    output_path = Path("outputs/json_test_summary.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "total_tests": total,
        "correct_predictions": correct,
        "accuracy_percent": round(accuracy, 2),
        "results": rows
    }

    output_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\nTest summary saved to: {output_path}")


if __name__ == "__main__":
    main()