# GlucoScan – analiza wyników glukozy z PDF i JSON

Projekt służy do analizy wyniku glukozy na podstawie:
- tekstowego pliku PDF z wynikami badań,
- pliku JSON z danymi testowymi.

Aplikacja:
- odczytuje wartość glukozy,
- porównuje ją z zakresem referencyjnym,
- określa status wyniku,
- generuje:
  - wynik na stronie WWW dla PDF,
  - `output.json`,
  - `report.html`.

## Zakres projektu

Obecna wersja projektu obsługuje:
- **tekstowe pliki PDF** odczytywane przy pomocy `pdfplumber`,
- **analizę plików JSON** uruchamianą z poziomu CLI.

## Uruchamianie

### JSON

```bash
python json_runner.py test_inputs/json/glu_high.json
```

### Aplikacja WWW dla PDF

```bash
python app.py
```

Po uruchomieniu aplikacji można przesłać plik PDF przez stronę WWW.

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

Instalacja:

```bash
pip install flask pdfplumber
```