const GLUCOSE_REF_LOW = 70;
const GLUCOSE_REF_HIGH = 99;
const MMOL_TO_MGDL = 18.018;

const examples = [
    {
        name: "glu_low.json",
        description: "Przykład wyniku poniżej normy.",
        data: {
            resourceType: "DiagnosticReport",
            patientId: "P001",
            description: "Test case for Glukoza",
            result: [
                {
                    code: "GLU",
                    name: "Glukoza",
                    value: 63,
                    unit: "mg/dL",
                    refLow: 70,
                    refHigh: 99,
                    expectedFlag: "L"
                }
            ]
        }
    },
    {
        name: "glu_normal.json",
        description: "Przykład wyniku w normie.",
        data: {
            resourceType: "DiagnosticReport",
            patientId: "P002",
            description: "Test case for Glukoza",
            result: [
                {
                    code: "GLU",
                    name: "Glukoza",
                    value: 91,
                    unit: "mg/dL",
                    refLow: 70,
                    refHigh: 99,
                    expectedFlag: "N"
                }
            ]
        }
    },
    {
        name: "glu_high.json",
        description: "Przykład wyniku powyżej normy.",
        data: {
            resourceType: "DiagnosticReport",
            patientId: "P003",
            description: "Test case for Glukoza",
            result: [
                {
                    code: "GLU",
                    name: "Glukoza",
                    value: 168,
                    unit: "mg/dL",
                    refLow: 70,
                    refHigh: 99,
                    expectedFlag: "H"
                }
            ]
        }
    },
    {
        name: "glu_mmol_normal.json",
        description: "Przykład wyniku w mmol/L w normie.",
        data: {
            resourceType: "DiagnosticReport",
            patientId: "P004",
            description: "Test case for Glucose",
            result: [
                {
                    code: "GLU",
                    name: "Glucose",
                    value: 5.1,
                    unit: "mmol/L",
                    refLow: 3.9,
                    refHigh: 5.5,
                    expectedFlag: "N"
                }
            ]
        }
    },
    {
        name: "glu_mmol_high.json",
        description: "Przykład wyniku w mmol/L powyżej normy.",
        data: {
            resourceType: "DiagnosticReport",
            patientId: "P005",
            description: "Test case for Glucose",
            result: [
                {
                    code: "GLU",
                    name: "Glucose",
                    value: 7.2,
                    unit: "mmol/L",
                    refLow: 3.9,
                    refHigh: 5.5,
                    expectedFlag: "H"
                }
            ]
        }
    }
];

let lastResult = null;

const jsonInput = document.getElementById("jsonInput");
const jsonFile = document.getElementById("jsonFile");
const runBtn = document.getElementById("runBtn");
const clearBtn = document.getElementById("clearBtn");
const resultBox = document.getElementById("resultBox");
const errorBox = document.getElementById("errorBox");
const downloadResultBtn = document.getElementById("downloadResultBtn");
const examplesList = document.getElementById("examplesList");

document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
        const tabName = button.dataset.tab;

        document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach((content) => content.classList.remove("active"));

        button.classList.add("active");
        document.getElementById(tabName).classList.add("active");
    });
});

jsonFile.addEventListener("change", async (event) => {
    const file = event.target.files[0];

    if (!file) {
        return;
    }

    const text = await file.text();
    jsonInput.value = text;
});

runBtn.addEventListener("click", () => {
    clearError();

    try {
        const data = JSON.parse(jsonInput.value);
        const glucose = extractGlucoseFromJson(data);
        const result = evaluate(glucose.value, glucose.unit, glucose.refLow, glucose.refHigh);

        result.expected_flag = glucose.expectedFlag || null;
        result.predicted_flag = result.flag;
        result.correct = result.expected_flag ? result.expected_flag === result.predicted_flag : null;
        result.source = "web_json_tester";

        lastResult = result;
        renderResult(result);
    } catch (error) {
        showError(error.message);
    }
});

clearBtn.addEventListener("click", () => {
    jsonInput.value = "";
    jsonFile.value = "";
    lastResult = null;
    clearError();
    downloadResultBtn.classList.add("hidden");
    resultBox.className = "result empty";
    resultBox.innerHTML = "Brak wyniku. Wklej JSON lub wybierz plik, a następnie kliknij „Analizuj JSON”.";
});

downloadResultBtn.addEventListener("click", () => {
    if (!lastResult) {
        return;
    }

    downloadJson("analysis_result.json", lastResult);
});

function extractGlucoseFromJson(data) {
    const results = data.result;

    if (!Array.isArray(results)) {
        throw new Error("Nie znaleziono tablicy result w pliku JSON.");
    }

    const glucose = results.find((item) => {
        const code = String(item.code || "").toUpperCase();
        const name = String(item.name || "").toLowerCase();

        return (
            code === "GLU" ||
            code === "GLC" ||
            name.includes("glukoza") ||
            name.includes("glucose")
        );
    });

    if (!glucose) {
        throw new Error("Nie znaleziono wyniku glukozy w pliku JSON.");
    }

    if (glucose.value === undefined || glucose.value === null) {
        throw new Error("Wynik glukozy nie zawiera pola value.");
    }

    return {
        value: glucose.value,
        unit: glucose.unit || "mg/dL",
        refLow: glucose.refLow,
        refHigh: glucose.refHigh,
        expectedFlag: glucose.expectedFlag || null
    };
}

function evaluate(value, unit, refLow = null, refHigh = null) {
    const validationErrors = [];

    let numericValue = Number(value);

    if (Number.isNaN(numericValue)) {
        validationErrors.push("Nieprawidłowa lub nieodczytana wartość glukozy.");
        numericValue = 0;
    }

    let finalUnit = unit;

    if (!finalUnit || String(finalUnit).trim() === "") {
        validationErrors.push("Nie odczytano jednostki wyniku, przyjęto domyślnie mg/dL.");
        finalUnit = "mg/dL";
    }

    const unitClean = String(finalUnit).trim().toLowerCase().replace(/\s/g, "");

    if (unitClean === "mg/dl" || unitClean === "mg/dl.") {
        finalUnit = "mg/dL";
    } else if (unitClean === "mmol/l" || unitClean === "mmol/l.") {
        finalUnit = "mmol/L";
    } else {
        validationErrors.push(`Nieobsługiwana jednostka wyniku: ${finalUnit}. Przyjęto domyślnie mg/dL.`);
        finalUnit = "mg/dL";
    }

    let low = refLow !== undefined && refLow !== null ? Number(refLow) : null;
    let high = refHigh !== undefined && refHigh !== null ? Number(refHigh) : null;

    if (Number.isNaN(low)) {
        low = null;
        validationErrors.push("Nieprawidłowa dolna granica zakresu referencyjnego.");
    }

    if (Number.isNaN(high)) {
        high = null;
        validationErrors.push("Nieprawidłowa górna granica zakresu referencyjnego.");
    }

    if (low === null) {
        low = GLUCOSE_REF_LOW;
        validationErrors.push("Nie odczytano dolnej granicy zakresu, użyto wartości domyślnej.");
    }

    if (high === null) {
        high = GLUCOSE_REF_HIGH;
        validationErrors.push("Nie odczytano górnej granicy zakresu, użyto wartości domyślnej.");
    }

    let valueMgdl;

    if (finalUnit === "mmol/L") {
        valueMgdl = numericValue * MMOL_TO_MGDL;

        if (high <= 30) {
            low = low * MMOL_TO_MGDL;
            high = high * MMOL_TO_MGDL;
        }
    } else {
        valueMgdl = numericValue;
    }

    if (valueMgdl < 20 || valueMgdl > 600) {
        validationErrors.push("Odczytana wartość glukozy znajduje się poza typowym zakresem kontrolnym 20–600 mg/dL.");
    }

    let status;
    let flag;
    let label;
    let advice;

    if (valueMgdl < low) {
        status = "low";
        flag = "L";
        label = "Za niska";
        advice = "Twój poziom glukozy jest poniżej normy (hipoglikemia). Skonsultuj się z lekarzem.";
    } else if (valueMgdl > high) {
        status = "high";
        flag = "H";
        label = "Za wysoka";
        advice = "Twój poziom glukozy jest powyżej normy. Może to wskazywać na stan przedcukrzycowy lub cukrzycę. Skonsultuj się z lekarzem.";
    } else {
        status = "normal";
        flag = "N";
        label = "W normie";
        advice = "Twój poziom glukozy jest prawidłowy.";
    }

    return {
        value: round(numericValue, 2),
        unit: finalUnit,
        value_mgdl: round(valueMgdl, 1),
        ref_low: round(low, 1),
        ref_high: round(high, 1),
        status,
        flag,
        label,
        advice,
        validation_errors: validationErrors
    };
}

function renderResult(result) {
    const flagClass = result.status;

    resultBox.className = "result";
    resultBox.innerHTML = `
        <div class="result-card">
            <p>Wynik glukozy:</p>
            <div class="value">${result.value}</div>
            <div class="unit">${result.unit}</div>

            <span class="flag ${flagClass}">Flaga: ${result.flag} — ${result.label}</span>

            <table class="result-table">
                <tr>
                    <th>Parametr</th>
                    <th>Wartość</th>
                </tr>
                <tr>
                    <td>Wartość po przeliczeniu</td>
                    <td>${result.value_mgdl} mg/dL</td>
                </tr>
                <tr>
                    <td>Zakres referencyjny</td>
                    <td>${result.ref_low} - ${result.ref_high} mg/dL</td>
                </tr>
                <tr>
                    <td>Przewidziana flaga</td>
                    <td>${result.predicted_flag}</td>
                </tr>
                <tr>
                    <td>Oczekiwana flaga</td>
                    <td>${result.expected_flag || "brak"}</td>
                </tr>
                <tr>
                    <td>Poprawność</td>
                    <td>${result.correct === null ? "brak flagi oczekiwanej" : result.correct ? "poprawny" : "niepoprawny"}</td>
                </tr>
            </table>

            <p><strong>Interpretacja:</strong> ${result.advice}</p>
            <p><strong>Walidacja:</strong> ${result.validation_errors.length ? result.validation_errors.join(" ") : "Brak błędów walidacji."}</p>
        </div>
    `;

    downloadResultBtn.classList.remove("hidden");
}

function renderExamples() {
    examplesList.innerHTML = "";

    examples.forEach((example) => {
        const card = document.createElement("div");
        card.className = "example-card";

        card.innerHTML = `
            <h3>${example.name}</h3>
            <p>${example.description}</p>
            <div class="example-actions">
                <button data-action="load">Wczytaj</button>
                <button data-action="download" class="secondary">Pobierz</button>
            </div>
        `;

        card.querySelector('[data-action="load"]').addEventListener("click", () => {
            jsonInput.value = JSON.stringify(example.data, null, 2);
            document.querySelector('[data-tab="test"]').click();
        });

        card.querySelector('[data-action="download"]').addEventListener("click", () => {
            downloadJson(example.name, example.data);
        });

        examplesList.appendChild(card);
    });
}

function downloadJson(filename, data) {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json"
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = filename;
    link.click();

    URL.revokeObjectURL(url);
}

function showError(message) {
    errorBox.textContent = message;
    errorBox.classList.remove("hidden");
}

function clearError() {
    errorBox.textContent = "";
    errorBox.classList.add("hidden");
}

function round(value, places) {
    const factor = 10 ** places;
    return Math.round(value * factor) / factor;
}

renderExamples();