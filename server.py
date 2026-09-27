
from flask import Flask, render_template, request, jsonify, send_from_directory
from pathlib import Path
import json, re, math, html
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "output"
app = Flask(__name__, template_folder="app/templates", static_folder="app/static")

def kdp_margins(pages, bleed=False):
    if pages <= 150: inside = 0.375
    elif pages <= 300: inside = 0.5
    elif pages <= 500: inside = 0.625
    elif pages <= 700: inside = 0.75
    else: inside = 0.875
    outside = 0.375 if bleed else 0.25
    return {"inside_in": inside, "outside_in": outside, "top_in": 0.75, "bottom_in": 0.75}

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

def cover_dimensions(width, height, pages, paper="white", interior="bw"):
    spine = spine_width(pages, paper, interior)
    bleed = 0.125
    return {
        "cover_width_in": round(bleed + width + spine + width + bleed, 4),
        "cover_height_in": round(bleed + height + bleed, 4),
        "spine_in": round(spine, 4),
        "bleed_in": bleed
    }

def slug(s):
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", s.strip())
    return s.strip("_") or "book"

def review_text(text):
    issues=[]
    for m in re.finditer(r"\b(\w+)(?:\s+\1\b)", text, re.I):
        issues.append({"type":"ripetizione","severity":"warning","message":f"Possibile ripetizione immediata: '{m.group(0)}'"})
    if "  " in text:
        issues.append({"type":"spaziatura","severity":"warning","message":"Doppio spazio rilevato."})
    if re.search(r"[!?]{3,}", text):
        issues.append({"type":"punteggiatura","severity":"warning","message":"Punteggiatura eccessiva."})
    return {"issues": issues, "score": max(0, 100-len(issues)*5)}

def build_sample_project(data):
    title=data.get("title") or "Il mio nuovo libro"
    pages=max(50, int(data.get("pages") or 60))
    width=float(data.get("width") or 6)
    height=float(data.get("height") or 9)
    bleed=bool(data.get("bleed"))
    margins=kdp_margins(pages, bleed)
    cover=cover_dimensions(width,height,pages,data.get("paper","white"),data.get("interior","bw"))
    theme=data.get("theme") or "Benessere"
    audience=data.get("audience") or "Adulti"
    activities=max(1,int(data.get("activities") or 30))
    chapters=max(1,min(12,math.ceil(pages/12)))
    sections=[]
    for i in range(chapters):
        sections.append({
            "number": i+1,
            "title": f"Capitolo {i+1} — {theme}",
            "purpose": "Contenuto, esempio pratico, schema e attività.",
            "activity": (i < activities)
        })
    return {
        "metadata": {
            "title": title, "subtitle": data.get("subtitle",""),
            "author": data.get("author",""), "language": data.get("language","Italiano"),
            "theme": theme, "audience": audience, "tone": data.get("tone","Professionale e accessibile"),
            "created_at": datetime.now().isoformat(timespec="seconds")
        },
        "spec": {"pages":pages,"trim_width_in":width,"trim_height_in":height,"bleed":bleed,
                 "paper":data.get("paper","white"),"interior":data.get("interior","bw"),
                 "margins":margins,"cover":cover},
        "editorial_profile": {
            "target": audience, "tone": data.get("tone","Professionale e accessibile"),
            "quality_target":"alto", "repetition_tolerance":"bassa",
            "review_loop":"Genera → analizza → correggi → ricontrolla"
        },
        "sections": sections
    }

@app.route("/")
def index(): return render_template("index.html")

@app.post("/api/plan")
def plan():
    data=request.get_json(force=True)
    return jsonify(build_sample_project(data))

@app.post("/api/review")
def review():
    data=request.get_json(force=True)
    text=data.get("text","")
    return jsonify(review_text(text))

@app.post("/api/cover")
def cover():
    data=request.get_json(force=True)
    return jsonify(cover_dimensions(float(data.get("width",6)),float(data.get("height",9)),
                                    int(data.get("pages",60)),data.get("paper","white"),data.get("interior","bw")))

@app.post("/api/export-project")
def export_project():
    data=request.get_json(force=True)
    project=build_sample_project(data)
    name=slug(project["metadata"]["title"])
    path=OUT/f"{name}_project.json"
    path.write_text(json.dumps(project,ensure_ascii=False,indent=2),encoding="utf-8")
    return jsonify({"file":path.name})

@app.get("/output/<path:name>")
def output(name):
    return send_from_directory(OUT,name,as_attachment=True)

if __name__=="__main__":
    app.run(host="127.0.0.1",port=5000,debug=False)
