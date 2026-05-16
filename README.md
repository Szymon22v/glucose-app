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