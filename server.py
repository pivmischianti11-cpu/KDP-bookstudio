from flask import Flask, render_template, request, jsonify, send_from_directory
from pathlib import Path
import json
import re
import math
from datetime import datetime

# ============================================================
# KDP BOOK STUDIO
# Backend principale
# ============================================================

BASE = Path(__file__).resolve().parent
OUT = BASE / "output"

# Crea automaticamente la cartella output
OUT.mkdir(parents=True, exist_ok=True)

app = Flask(
    __name__,
    template_folder="app/templates",
    static_folder="app/static"
)


# ============================================================
# FUNZIONI KDP
# ============================================================

def kdp_margins(pages, bleed=False):
    """
    Calcolo preliminare dei margini interni.
    I valori definitivi devono sempre essere verificati
    con le specifiche KDP aggiornate prima della pubblicazione.
    """

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
    """
    Calcolo preliminare del dorso.

    ATTENZIONE:
    questo è un calcolo tecnico preliminare.
    Per la copertina finale bisogna verificare i valori
    tramite il Cover Calculator KDP aggiornato.
    """

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
    """
    Calcola le dimensioni preliminari della copertina completa.
    """

    spine = spine_width(
        pages,
        paper,
        interior
    )

    bleed = 0.125

    cover_width = (
        bleed
        + width
        + spine
        + width
        + bleed
    )

    cover_height = (
        bleed
        + height
        + bleed
    )

    return {
        "cover_width_in": round(
            cover_width,
            4
        ),

        "cover_height_in": round(
            cover_height,
            4
        ),

        "spine_in": round(
            spine,
            4
        ),

        "bleed_in": bleed,

        "note": (
            "Dimensioni preliminari. "
            "Verificare sempre il Cover Calculator "
            "KDP prima della pubblicazione."
        )
    }


# ============================================================
# UTILITY
# ============================================================

def slug(value):
    """
    Trasforma il titolo in un nome file sicuro.
    """

    value = str(value).strip()

    value = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        value
    )

    value = value.strip("_")

    return value or "book"


def safe_number(value, default):
    """
    Converte un valore numerico senza mandare
    il server in errore.
    """

    try:
        return float(value)

    except (
        TypeError,
        ValueError
    ):
        return default


# ============================================================
# REVISIONE TESTUALE
# ============================================================

def review_text(text):

    text = str(text or "")

    issues = []

    # --------------------------------------------------------
    # Parole ripetute immediatamente
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Doppi spazi
    # --------------------------------------------------------

    if re.search(
        r" {2,}",
        text
    ):

        issues.append({
            "type": "spaziatura",
            "severity": "warning",
            "message": "Doppio spazio rilevato."
        })

    # --------------------------------------------------------
    # Punteggiatura eccessiva
    # --------------------------------------------------------

    if re.search(
        r"[!?]{3,}",
        text
    ):

        issues.append({
            "type": "punteggiatura",
            "severity": "warning",
            "message": "Punteggiatura eccessiva."
        })

    # --------------------------------------------------------
    # Sequenze di punti
    # --------------------------------------------------------

    if re.search(
        r"\.{4,}",
        text
    ):

        issues.append({
            "type": "punteggiatura",
            "severity": "warning",
            "message": "Sequenza di punti eccessiva."
        })

    # --------------------------------------------------------
    # Statistiche
    # --------------------------------------------------------

    sentences = [
        sentence.strip()
        for sentence in re.split(
            r"[.!?]+",
            text
        )
        if sentence.strip()
    ]

    words = re.findall(
        r"\b\w+\b",
        text,
        re.UNICODE
    )

    score = max(
        0,
        100 - len(issues) * 5
    )

    return {
        "issues": issues,

        "score": score,

        "stats": {
            "words": len(words),
            "sentences": len(sentences),
            "characters": len(text)
        }
    }


# ============================================================
# COSTRUZIONE DEL PROGETTO
# ============================================================

def build_project(data):

    title = str(
        data.get("title")
        or "Il mio nuovo libro"
    ).strip()

    subtitle = str(
        data.get("subtitle")
        or ""
    ).strip()

    author = str(
        data.get("author")
        or ""
    ).strip()

    theme = str(
        data.get("theme")
        or "Benessere"
    ).strip()

    audience = str(
        data.get("audience")
        or "Adulti"
    ).strip()

    tone = str(
        data.get("tone")
        or "Professionale e accessibile"
    ).strip()

    pages = max(
        50,
        int(
            safe_number(
                data.get("pages"),
                60
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

    activities = max(
        0,
        int(
            safe_number(
                data.get("activities"),
                20
            )
        )
    )

    bleed = bool(
        data.get("bleed", False)
    )

    paper = data.get(
        "paper",
        "white"
    )

    interior = data.get(
        "interior",
        "bw"
    )

    # --------------------------------------------------------
    # Numero capitoli
    # --------------------------------------------------------

    chapters = max(
        1,
        min(
            20,
            math.ceil(
                pages / 10
            )
        )
    )

    sections = []

    for index in range(chapters):

        sections.append({

            "number": index + 1,

            "title": (
                f"Capitolo {index + 1} "
                f"— {theme}"
            ),

            "purpose": (
                "Spiegazione, esempio pratico, "
                "elemento visivo e attività."
            ),

            "estimated_pages": max(
                2,
                pages // chapters
            ),

            "activity": (
                index < activities
            )
        })

    # --------------------------------------------------------
    # Progetto completo
    # --------------------------------------------------------

    project = {

        "metadata": {

            "title": title,

            "subtitle": subtitle,

            "author": author,

            "language": data.get(
                "language",
                "Italiano"
            ),

            "theme": theme,

            "audience": audience,

            "tone": tone,

            "created_at": (
                datetime.now()
                .isoformat(
                    timespec="seconds"
                )
            )
        },

        "spec": {

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

        "editorial_profile": {

            "target": audience,

            "tone": tone,

            "quality_target": "alto",

            "repetition_tolerance": "bassa",

            "review_loop": (
                "Genera → analizza → "
                "correggi → ricontrolla"
            )
        },

        "sections": sections
    }

    return project


# ============================================================
# PAGINA PRINCIPALE
# ============================================================

@app.get("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return jsonify({

        "status": "ok",

        "service": "KDP Book Studio",

        "version": "1.0"
    })


# ============================================================
# GENERAZIONE STRUTTURA
# ============================================================

@app.post("/api/plan")
def plan():

    data = request.get_json(
        force=True
    ) or {}

    project = build_project(
        data
    )

    return jsonify(
        project
    )


# ============================================================
# REVISIONE TESTO
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
# CALCOLO COPERTINA
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

    paper = data.get(
        "paper",
        "white"
    )

    interior = data.get(
        "interior",
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
# ESPORTAZIONE PROGETTO
# ============================================================

@app.post("/api/export-project")
def export_project():

    data = request.get_json(
        force=True
    ) or {}

    project = build_project(
        data
    )

    filename = (
        f"{slug(project['metadata']['title'])}"
        "_project.json"
    )

    path = OUT / filename

    path.write_text(
        json.dumps(
            project,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return jsonify({

        "file": filename,

        "url": (
            f"/output/{filename}"
        )
    })


# ============================================================
# DOWNLOAD FILE
# ============================================================

@app.get("/output/<path:name>")
def output(name):

    return send_from_directory(
        OUT,
        name,
        as_attachment=True
    )


# ============================================================
# AVVIO SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
