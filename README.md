# Analizator dokumentacji medycznej – analiza wyników glukozy z PDF, obrazów i JSON

Projekt służy do automatycznej analizy wyniku glukozy zapisanego w dokumentacji medycznej.

Aplikacja obsługuje:
- tekstowe pliki PDF z wynikami badań,
- skanowane pliki PDF,
- obrazy lub zdjęcia wyników badań w formacie PNG, JPG lub JPEG,
- pliki JSON z danymi testowymi.

System:
- odczytuje wartość glukozy,
- odczytuje tekst z PDF-ów, skanów i obrazów,
- rozpoznaje jednostkę wyniku,
- obsługuje jednostki `mg/dL` oraz `mmol/L`,
- przelicza wartości `mmol/L` na `mg/dL`,
- porównuje wynik z zakresem referencyjnym,
- przypisuje flagę:
  - `L` – wynik poniżej normy,
  - `N` – wynik w normie,
  - `H` – wynik powyżej normy,
- generuje:
  - wynik na stronie WWW dla PDF, skanu lub obrazu,
  - uporządkowany plik JSON,
  - raport HTML.

---

## Zakres projektu

Obecna wersja projektu obsługuje:

- **tekstowe pliki PDF** odczytywane przy pomocy `pdfplumber`,
- **skanowane pliki PDF** odczytywane przy pomocy EasyOCR i PyMuPDF,
- **obrazy i zdjęcia wyników badań** w formacie `.png`, `.jpg`, `.jpeg` odczytywane przy pomocy EasyOCR,
- **analizę plików JSON** uruchamianą z poziomu CLI,
- **webowy tester JSON** działający jako osobna strona HTML/JavaScript.

Projekt został zawężony do analizy jednego parametru laboratoryjnego: glukozy.

---

## Struktura projektu

```text
glucose-app/
│
├── app.py
├── logic.py
├── json_runner.py
├── run_json_tests.py
├── run_pdf_tests.py
├── run_image_tests.py
├── requirements.txt
├── README.md
│
├── test_inputs/
│   ├── json/
│   ├── pdf/
│   └── images/
│
├── outputs/
│   └── summaries/
│
├── reports/
│   ├── json/
│   ├── pdf/
│   └── images/
│
└── web_json_tester/
    ├── index.html
    ├── style.css
    ├── app.js
    └── examples/
```

---

## Uruchamianie głównej aplikacji

### Aplikacja WWW dla PDF, skanów i obrazów

```bash
python app.py
```

Na Windowsie można użyć:

```bash
py app.py
```

Po uruchomieniu aplikacji można przesłać przez stronę WWW:
- plik PDF,
- skanowany PDF,
- obraz PNG,
- obraz JPG lub JPEG.

Domyślnie aplikacja działa pod adresem:

```bash
http://127.0.0.1:5000
```

---

## Analiza pojedynczego pliku JSON z poziomu CLI

```bash
python json_runner.py test_inputs/json/glu_high.json
```

Na Windowsie można użyć:

```bash
py json_runner.py test_inputs/json/glu_high.json
```

Program analizuje wskazany plik JSON, odczytuje wynik glukozy, jednostkę i zakres referencyjny, a następnie zwraca wynik klasyfikacji.

---

## Webowy tester JSON

Projekt zawiera dodatkowy moduł:

```text
web_json_tester/
```

Jest to prosta strona internetowa służąca do testowania danych wejściowych w formacie JSON bez uruchamiania aplikacji Flask.

Tester umożliwia:
- wklejenie własnego JSON-a,
- wczytanie pliku `.json` z komputera,
- pobranie przykładowych danych testowych,
- uruchomienie analizy bez użycia komendy `python app.py`,
- wyświetlenie wyniku analizy bezpośrednio w przeglądarce,
- pobranie wyniku analizy jako plik JSON.

Moduł `web_json_tester` działa w przeglądarce i służy wyłącznie do testowania plików JSON. Nie obsługuje PDF-ów, skanów ani obrazów.

### Uruchomienie lokalne webowego testera JSON

Można otworzyć plik:

```text
web_json_tester/index.html
```

bezpośrednio w przeglądarce.

Można też użyć rozszerzenia Live Server w Visual Studio Code.

### Wersja na serwerze student

Po wrzuceniu folderu `web_json_tester` na serwer student strona może być dostępna pod adresem:

```text
https://student.agh.edu.pl/~dlubak/telemedycyna/json_tester/
```

---

## Testowanie

Projekt zawiera trzy zestawy danych testowych:

- `test_inputs/json` – pliki JSON,
- `test_inputs/pdf` – pliki PDF,
- `test_inputs/images` – obrazy JPG/PNG/JPEG.

Testy można uruchomić osobno dla każdego typu danych.

---

### Testy JSON

```bash
python run_json_tests.py
```

Na Windowsie można użyć:

```bash
py run_json_tests.py
```

Po uruchomieniu testów generowane są:
- podsumowanie testów w pliku `outputs/summaries/json_test_summary.json`,
- raporty HTML w folderze `reports/json`.

---

### Testy PDF

```bash
python run_pdf_tests.py
```

Na Windowsie można użyć:

```bash
py run_pdf_tests.py
```

Po uruchomieniu testów generowane są:
- podsumowanie testów w pliku `outputs/summaries/pdf_test_summary.json`,
- raporty HTML w folderze `reports/pdf`.

---

### Testy obrazów

```bash
python run_image_tests.py
```

Na Windowsie można użyć:

```bash
py run_image_tests.py
```

Po uruchomieniu testów generowane są:
- podsumowanie testów w pliku `outputs/summaries/image_test_summary.json`,
- raporty HTML w folderze `reports/images`.

---

## Wyniki testów

W aktualnej wersji projektu testy zostały przygotowane dla trzech zestawów danych:
- JSON,
- PDF,
- obrazy JPG/PNG/JPEG.

Dla każdego zestawu przygotowano 8 przykładów testowych. Łącznie wykonano 24 testy.

Testy sprawdzają, czy aplikacja poprawnie:
- odczytuje wynik glukozy,
- rozpoznaje jednostkę,
- przelicza `mmol/L` na `mg/dL`,
- porównuje wynik z zakresem referencyjnym,
- przypisuje właściwą flagę:
  - `L` – wynik poniżej normy,
  - `N` – wynik w normie,
  - `H` – wynik powyżej normy.

W aktualnym zestawie testowym aplikacja uzyskała:

```text
JSON:   8/8 poprawnych klasyfikacji
PDF:    8/8 poprawnych klasyfikacji
Obrazy: 8/8 poprawnych klasyfikacji

Łącznie: 24/24 poprawnych klasyfikacji
Skuteczność: 100%
```

Podsumowania testów są zapisywane w folderze:

```bash
outputs/summaries
```

Raporty HTML wygenerowane podczas testów są zapisywane w folderach:

```bash
reports/json
reports/pdf
reports/images
```

---

## Walidacja HTML

Przykładowy raport HTML wygenerowany przez aplikację został sprawdzony walidatorem HTML5.

Walidacja nie wykazała błędów ani ostrzeżeń, co potwierdziło poprawność struktury wygenerowanego dokumentu HTML.

---

## Wymagania

Należy mieć zainstalowane:

- Python 3.x

Biblioteki użyte w projekcie:

- Flask
- pdfplumber
- EasyOCR
- PyTorch
- torchvision
- PyMuPDF
- Pillow
- NumPy

Instalacja zależności:

```bash
python -m pip install -r requirements.txt
```

Na Windowsie można użyć:

```bash
py -m pip install -r requirements.txt
```

---

## Uwagi dotyczące OCR

Skuteczność OCR zależy od jakości pliku wejściowego.

Najlepsze wyniki uzyskuje się dla dokumentów, które są:

- ostre,
- dobrze oświetlone,
- zapisane w dobrej rozdzielczości,
- wykonane prosto, bez dużego przechylenia,
- bez mocnych cieni i rozmycia.

W przypadku bardzo słabej jakości zdjęcia lub skanu aplikacja może nie odczytać poprawnie wartości glukozy, jednostki albo zakresu referencyjnego.

---

## Ograniczenia projektu

Obecna wersja projektu analizuje wyłącznie wynik glukozy.

Aplikacja nie jest systemem medycznym i nie zastępuje konsultacji z lekarzem. Wynik generowany przez program ma charakter edukacyjny i demonstracyjny.

Webowy tester JSON działa wyłącznie dla danych w formacie JSON i nie obsługuje OCR, PDF-ów ani obrazów.

---

## Autorzy

Projekt wykonany w ramach przedmiotu **Podstawy telemedycyny**.

Autorzy:
- Oliwia Frączek-Warias,
- Szymon Młynek,
- Kamil Dłubak.