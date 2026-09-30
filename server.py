from flask import Flask, render_template, request, jsonify, send_from_directory
from pathlib import Path
import json
import re
import math
from datetime import datetime

# ============================================================
# KDP BOOK STUDIO — BOOK ENGINE 1.0
# ============================================================

BASE = Path(__file__).resolve().parent
OUT = BASE / "output"
OUT.mkdir(parents=True, exist_ok=True)

app = Flask(
    __name__,
    template_folder="app/templates",
    static_folder="app/static"
)


# ============================================================
# UTILITY
# ============================================================

def slug(value):
    value = str(value or "").strip()
    value = re.sub(r"[^a-zA-Z0-9À-ÿ_-]+", "_", value)
    value = value.strip("_")
    return value or "book"


def safe_number(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clean_text(value, default=""):
    value = str(value or "").strip()
    return value if value else default


# ============================================================
# KDP
# ============================================================

def kdp_margins(pages, bleed=False):

    if pages <= 150:
        inside = 0.375
    elif pages <= 300:
        inside = 0.5
    elif pages <= 500:
        inside = 0.625
    elif pages <= 700:
        inside = 0.75
    else:
        inside = 0.875

    outside = 0.375 if bleed else 0.25

    return {
        "inside_in": inside,
        "outside_in": outside,
        "top_in": 0.75,
        "bottom_in": 0.75
    }


def spine_width(pages, paper="white", interior="bw"):

    if interior == "premium_color":
        factor = 0.002347
    elif interior == "standard_color":
        factor = 0.002252
    elif paper == "cream":
        factor = 0.0025
    else:
        factor = 0.002252

    return pages * factor


def cover_dimensions(
    width,
    height,
    pages,
    paper="white",
    interior="bw"
):

    spine = spine_width(
        pages,
        paper,
        interior
    )

    bleed = 0.125

    return {
        "cover_width_in": round(
            bleed + width + spine + width + bleed,
            4
        ),

        "cover_height_in": round(
            bleed + height + bleed,
            4
        ),

        "spine_in": round(spine, 4),

        "bleed_in": bleed,

        "note": (
            "Dimensioni preliminari. "
            "Prima della pubblicazione verificare "
            "sempre le specifiche KDP aggiornate."
        )
    }


# ============================================================
# REVISIONE TESTUALE
# ============================================================

def review_text(text):

    text = str(text or "")
    issues = []

    # Ripetizioni immediate
    for match in re.finditer(
        r"\b(\w+)(?:\s+\1\b)",
        text,
        re.IGNORECASE
    ):
        issues.append({
            "type": "ripetizione",
            "severity": "warning",
            "message": (
                f"Possibile ripetizione immediata: "
                f"'{match.group(0)}'"
            )
        })

    # Doppi spazi
    if re.search(r" {2,}", text):
        issues.append({
            "type": "spaziatura",
            "severity": "warning",
            "message": "Doppio spazio rilevato."
        })

    # Punteggiatura
    if re.search(r"[!?]{3,}", text):
        issues.append({
            "type": "punteggiatura",
            "severity": "warning",
            "message": "Punteggiatura eccessiva."
        })

    if re.search(r"\.{4,}", text):
        issues.append({
            "type": "punteggiatura",
            "severity": "warning",
            "message": "Sequenza di punti eccessiva."
        })

    words = re.findall(
        r"\b\w+\b",
        text,
        re.UNICODE
    )

    sentences = [
        x.strip()
        for x in re.split(
            r"[.!?]+",
            text
        )
        if x.strip()
    ]

    score = max(
        0,
        100 - len(issues) * 5
    )

    return {
        "score": score,
        "issues": issues,
        "stats": {
            "words": len(words),
            "sentences": len(sentences),
            "characters": len(text)
        }
    }


# ============================================================
# STRUTTURA DEL LIBRO
# ============================================================

def generate_chapters(
    title,
    theme,
    audience,
    tone,
    pages,
    activities
):

    chapters_count = max(
        5,
        min(
            20,
            math.ceil(pages / 10)
        )
    )

    chapters = []

    for i in range(1, chapters_count + 1):

        chapters.append({
            "number": i,
            "title": f"Capitolo {i} — {theme}",
            "introduction": (
                f"In questo capitolo affrontiamo "
                f"un aspetto importante di {theme}, "
                f"con un approccio {tone.lower()} "
                f"pensato per {audience.lower()}."
            ),

            "sections": [
                {
                    "title": "Il punto di partenza",
                    "content": (
                        f"Comprendere {theme} significa "
                        f"prima di tutto fermarsi a osservare "
                        f"la situazione con maggiore attenzione. "
                        f"Questo capitolo introduce i concetti "
                        f"fondamentali e li collega alla vita "
                        f"quotidiana del lettore."
                    )
                },

                {
                    "title": "Comprendere il problema",
                    "content": (
                        "Ogni cambiamento significativo nasce "
                        "dalla capacità di riconoscere ciò che "
                        "funziona e ciò che invece deve essere "
                        "modificato. In questa sezione il lettore "
                        "viene accompagnato passo dopo passo "
                        "nell'analisi."
                    )
                },

                {
                    "title": "Passare all'azione",
                    "content": (
                        "La conoscenza diventa realmente utile "
                        "quando viene trasformata in un'azione "
                        "concreta. Per questo motivo è importante "
                        "procedere con obiettivi chiari, realistici "
                        "e verificabili."
                    )
                }
            ],

            "activity": (
                i <= activities
            ),

            "activity_text": (
                f"ESERCIZIO — Capitolo {i}\n\n"
                f"Scrivi tre cose che hai compreso "
                f"su {theme} e indica una piccola azione "
                f"che puoi mettere in pratica."
            )
        })

    return chapters


# ============================================================
# COSTRUZIONE LIBRO
# ============================================================

def build_book(data):

    title = clean_text(
        data.get("title"),
        "Il mio nuovo libro"
    )

    subtitle = clean_text(
        data.get("subtitle")
    )

    author = clean_text(
        data.get("author"),
        "Autore"
    )

    theme = clean_text(
        data.get("theme"),
        "Crescita personale"
    )

    audience = clean_text(
        data.get("audience"),
        "Adulti"
    )

    tone = clean_text(
        data.get("tone"),
        "Professionale e accessibile"
    )

    language = clean_text(
        data.get("language"),
        "Italiano"
    )

    pages = max(
        50,
        int(
            safe_number(
                data.get("pages"),
                60
            )
        )
    )

    activities = max(
        0,
        int(
            safe_number(
                data.get("activities"),
                10
            )
        )
    )

    width = safe_number(
        data.get("width"),
        6
    )

    height = safe_number(
        data.get("height"),
        9
    )

    bleed = bool(
        data.get("bleed", False)
    )

    paper = clean_text(
        data.get("paper"),
        "white"
    )

    interior = clean_text(
        data.get("interior"),
        "bw"
    )

    # --------------------------------------------------------
    # Capitoli
    # --------------------------------------------------------

    chapters = generate_chapters(
        title,
        theme,
        audience,
        tone,
        pages,
        activities
    )

    # --------------------------------------------------------
    # Indice
    # --------------------------------------------------------

    toc = []

    for chapter in chapters:

        toc.append({
            "number": chapter["number"],
            "title": chapter["title"]
        })

    # --------------------------------------------------------
    # Libro
    # --------------------------------------------------------

    book = {

        "metadata": {

            "title": title,

            "subtitle": subtitle,

            "author": author,

            "language": language,

            "theme": theme,

            "audience": audience,

            "tone": tone,

            "created_at": datetime.now().isoformat(
                timespec="seconds"
            )
        },

        "kdp": {

            "pages_target": pages,

            "trim_width_in": width,

            "trim_height_in": height,

            "bleed": bleed,

            "paper": paper,

            "interior": interior,

            "margins": kdp_margins(
                pages,
                bleed
            ),

            "cover": cover_dimensions(
                width,
                height,
                pages,
                paper,
                interior
            )
        },

        "front_matter": {

            "title_page": title,

            "copyright": (
                f"© {datetime.now().year} {author}. "
                "Tutti i diritti riservati."
            ),

            "introduction": (
                f"Benvenuto in «{title}».\n\n"
                f"Questo libro è stato progettato per "
                f"accompagnare il lettore nell'esplorazione "
                f"di {theme}, attraverso spiegazioni, "
                f"riflessioni ed esercizi pratici."
            )
        },

        "table_of_contents": toc,

        "chapters": chapters,

        "conclusion": (
            f"Arrivato alla fine di questo percorso su "
            f"{theme}, il passo più importante è trasformare "
            "ciò che hai letto in qualcosa di concreto. "
            "Anche un piccolo cambiamento può diventare "
            "l'inizio di un percorso più ampio."
        ),

        "editorial": {

            "quality_target": "alto",

            "repetition_tolerance": "bassa",

            "review_loop": (
                "Genera → analizza → correggi → "
                "ricontrolla"
            ),

            "status": "bozza generata"
        }
    }

    return book


# ============================================================
# TESTO COMPLETO DEL LIBRO
# ============================================================

def book_to_text(book):

    lines = []

    meta = book["metadata"]

    lines.append(meta["title"])
    lines.append("")

    if meta["subtitle"]:
        lines.append(meta["subtitle"])
        lines.append("")

    lines.append(f"Autore: {meta['author']}")
    lines.append("")
    lines.append("=" * 60)
    lines.append("")

    lines.append("COPYRIGHT")
    lines.append("")
    lines.append(
        book["front_matter"]["copyright"]
    )
    lines.append("")

    lines.append("INTRODUZIONE")
    lines.append("")
    lines.append(
        book["front_matter"]["introduction"]
    )
    lines.append("")

    lines.append("INDICE")
    lines.append("")

    for item in book["table_of_contents"]:

        lines.append(
            f"{item['number']}. {item['title']}"
        )

    lines.append("")

    for chapter in book["chapters"]:

        lines.append("=" * 60)

        lines.append(
            chapter["title"]
        )

        lines.append("=" * 60)
        lines.append("")

        lines.append(
            chapter["introduction"]
        )

        lines.append("")

        for section in chapter["sections"]:

            lines.append(
                section["title"]
            )

            lines.append("")

            lines.append(
                section["content"]
            )

            lines.append("")

        if chapter["activity"]:

            lines.append(
                chapter["activity_text"]
            )

            lines.append("")

    lines.append("=" * 60)
    lines.append("CONCLUSIONE")
    lines.append("=" * 60)
    lines.append("")

    lines.append(
        book["conclusion"]
    )

    return "\n".join(lines)


# ============================================================
# PAGINA PRINCIPALE
# ============================================================

@app.get("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return jsonify({
        "status": "ok",
        "service": "KDP Book Studio",
        "version": "2.0-book-engine"
    })


# ============================================================
# GENERA STRUTTURA
# ============================================================

@app.post("/api/plan")
def plan():

    data = request.get_json(
        force=True
    ) or {}

    book = build_book(data)

    return jsonify(book)


# ============================================================
# GENERA LIBRO
# ============================================================

@app.post("/api/generate-book")
def generate_book():

    data = request.get_json(
        force=True
    ) or {}

    book = build_book(data)

    text = book_to_text(book)

    filename = (
        f"{slug(book['metadata']['title'])}"
        "_manoscritto.txt"
    )

    path = OUT / filename

    path.write_text(
        text,
        encoding="utf-8"
    )

    return jsonify({

        "status": "ok",

        "message": (
            "Manoscritto generato."
        ),

        "file": filename,

        "url": f"/output/{filename}",

        "book": book
    })


# ============================================================
# REVISIONE
# ============================================================

@app.post("/api/review")
def review():

    data = request.get_json(
        force=True
    ) or {}

    text = data.get(
        "text",
        ""
    )

    return jsonify(
        review_text(text)
    )


# ============================================================
# COPERTINA
# ============================================================

@app.post("/api/cover")
def cover():

    data = request.get_json(
        force=True
    ) or {}

    width = safe_number(
        data.get("width"),
        6
    )

    height = safe_number(
        data.get("height"),
        9
    )

    pages = int(
        safe_number(
            data.get("pages"),
            60
        )
    )

    paper = clean_text(
        data.get("paper"),
        "white"
    )

    interior = clean_text(
        data.get("interior"),
        "bw"
    )

    return jsonify(
        cover_dimensions(
            width,
            height,
            pages,
            paper,
            interior
        )
    )


# ============================================================
# SALVA PROGETTO
# ============================================================

@app.post("/api/export-project")
def export_project():

    data = request.get_json(
        force=True
    ) or {}

    book = build_book(data)

    filename = (
        f"{slug(book['metadata']['title'])}"
        "_project.json"
    )

    path = OUT / filename

    path.write_text(
        json.dumps(
            book,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return jsonify({

        "file": filename,

        "url": f"/output/{filename}"
    })


# ============================================================
# DOWNLOAD
# ============================================================

@app.get("/output/<path:name>")
def output(name):

    return send_from_directory(
        OUT,
        name,
        as_attachment=True
    )


# ============================================================
# AVVIO
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
        )
