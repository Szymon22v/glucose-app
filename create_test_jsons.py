import json
from pathlib import Path

output_dir = Path("test_inputs/json")
output_dir.mkdir(parents=True, exist_ok=True)

test_cases = {
    "glu_low.json": (63, "mg/dL", "L", "Glukoza"),
    "glu_normal.json": (91, "mg/dL", "N", "Glukoza"),
    "glu_high.json": (168, "mg/dL", "H", "Glukoza"),
    "glu_very_low.json": (45, "mg/dL", "L", "Glukoza"),
    "glu_very_high.json": (265, "mg/dL", "H", "Glukoza"),
    "glu_border_low.json": (70, "mg/dL", "N", "Glukoza"),
    "glu_border_high.json": (99, "mg/dL", "N", "Glukoza"),
    "glu_mmol_normal.json": (5.1, "mmol/L", "N", "Glucose"),
    "glu_mmol_high.json": (7.2, "mmol/L", "H", "Glucose"),
    "glu_fasting_normal.json": (85, "mg/dL", "N", "Glukoza na czczo"),
}

for i, (filename, (value, unit, expected_flag, name)) in enumerate(test_cases.items(), start=1):
    data = {
        "resourceType": "DiagnosticReport",
        "patientId": f"P{i:03d}",
        "description": f"Test case for {name}",
        "result": [
            {
                "code": "GLU",
                "name": name,
                "value": value,
                "unit": unit,
                "refLow": 70,
                "refHigh": 99,
                "expectedFlag": expected_flag
            }
        ]
    }

    path = output_dir / filename
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Created: {path}")

print("Done.")