
# KDP Book Studio 2.0 — architettura iniziale

Questa è una base funzionante per trasformare il prototipo in un vero generatore editoriale.

## Avvio
1. Installa Python 3.10+.
2. `pip install -r requirements.txt`
3. `python server.py`
4. Apri `http://127.0.0.1:5000`

## Cosa contiene già
- wizard web responsive;
- progetto strutturato in JSON;
- calcolo margini in funzione delle pagine;
- calcolo preliminare del dorso/copertina;
- preflight tecnico;
- revisore testuale iniziale;
- esportazione del progetto.

## Architettura prevista
BRIEF → OUTLINE → WRITER → IMAGE ENGINE → EDITOR → CONSISTENCY CHECKER → LAYOUT ENGINE → PDF/DOCX → COVER ENGINE → KDP QA.

## Prossimo livello
Per la generazione reale del libro occorre collegare:
- un modello linguistico tramite backend;
- un provider di immagini;
- renderer PDF/DOCX;
- motore di impaginazione pagina-per-pagina;
- controllo immagini/risoluzione;
- controllo ripetizioni semantiche;
- controllo riferimenti incrociati;
- generatore di puzzle e soluzioni;
- gestione progetti/versioni.

NON mettere mai una chiave API nel JavaScript del browser.

Le dimensioni KDP devono essere ricontrollate contro le specifiche ufficiali correnti e il Print Previewer prima della pubblicazione.
