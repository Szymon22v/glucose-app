# GlucoScan – analiza wyników glukozy z PDF, obrazów i JSON

Projekt służy do analizy wyniku glukozy na podstawie:
- tekstowego pliku PDF z wynikami badań,
- skanowanego pliku PDF,
- obrazu lub zdjęcia wyników badań w formacie PNG, JPG lub JPEG,
- pliku JSON z danymi testowymi.

Aplikacja:
- odczytuje wartość glukozy,
- odczytuje tekst z PDF-ów, skanów i obrazów,
- porównuje ją z zakresem referencyjnym,
- określa status wyniku,
- generuje:
  - wynik na stronie WWW dla PDF, skanu lub obrazu,
  - `output.json`,
  - `report.html`.

## Zakres projektu

Obecna wersja projektu obsługuje:
- **tekstowe pliki PDF** odczytywane przy pomocy `pdfplumber`,
- **skanowane pliki PDF** odczytywane przy pomocy OCR,
- **obrazy i zdjęcia wyników badań** w formacie `.png`, `.jpg`, `.jpeg` odczytywane przy pomocy OCR,
- **analizę plików JSON** uruchamianą z poziomu CLI.

## Uruchamianie

### JSON

```bash
python json_runner.py test_inputs/json/glu_high.json
```

Na Windowsie można użyć:

```bash
py json_runner.py test_inputs/json/glu_high.json
```

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

## Testowanie

Projekt zawiera trzy zestawy danych testowych:
- `test_inputs/json` – pliki JSON,
- `test_inputs/pdf` – pliki PDF,
- `test_inputs/images` – obrazy JPG/PNG/JPEG.

Testy można uruchomić osobno dla każdego typu danych.

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

### Wyniki testów

W aktualnej wersji projektu testy zostały przygotowane dla 3 zestawów danych:
- JSON,
- PDF,
- obrazy JPG/PNG/JPEG.

Dla każdego zestawu przygotowano 10 przykładów testowych. Testy sprawdzają, czy aplikacja poprawnie odczytuje wynik glukozy, jednostkę oraz przypisuje właściwą flagę:
- `L` – wynik poniżej normy,
- `N` – wynik w normie,
- `H` – wynik powyżej normy.

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

## Wymagania

Należy mieć zainstalowane:
- Python 3.x

Biblioteki:
- Flask
- pdfplumber
- EasyOCR
- PyTorch
- torchvision
- PyMuPDF
- Pillow
- NumPy

Instalacja:

```bash
python -m pip install -r requirements.txt
```

Na Windowsie można użyć:

```bash
py -m pip install -r requirements.txt
```

## Uwagi dotyczące OCR

Skuteczność OCR zależy od jakości pliku wejściowego.

Najlepsze wyniki uzyskuje się dla dokumentów, które są:
- ostre,
- dobrze oświetlone,
- zapisane w dobrej rozdzielczości,
- wykonane prosto, bez dużego przechylenia,
- bez mocnych cieni i rozmycia.

W przypadku bardzo słabej jakości zdjęcia lub skanu aplikacja może nie odczytać poprawnie wartości glukozy.

---