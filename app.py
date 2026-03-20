from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import uuid
from datetime import date, timedelta
from ai_explainer import (
    generate_explanation,
    generate_related_terms,
    generate_followup_answer
)

app = Flask(__name__)
app.secret_key = "conceptclarity-secret-key"

TRENDING_CONCEPTS = [
    "CRISPR", "Quantum Entanglement", "Neuroplasticity",
    "Dark Matter", "Epigenetics", "Blockchain", "Mitochondria",
    "String Theory", "Osmosis", "Entropy"
]


def group_history(history):
    today     = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    grouped   = {"Today": [], "Yesterday": [], "Earlier": []}
    for item in history:
        d = item.get("date")
        if d == today:          grouped["Today"].append(item)
        elif d == yesterday:    grouped["Yesterday"].append(item)
        else:                   grouped["Earlier"].append(item)
    return grouped


@app.route("/", methods=["GET", "POST"])
def home():
    if "history" not in session:
        session["history"] = []
    for item in session["history"]:
        if "date" not in item:
            item["date"] = date.today().isoformat()

    if request.method == "POST":
        term       = request.form.get("term", "").strip()
        difficulty = request.form.get("difficulty", "intermediate")
        language   = request.form.get("language", "English")
        try:
            result = generate_explanation(term, difficulty, language)
            session["history"] = [h for h in session["history"] if h["term"].lower() != term.lower()]
            session["history"].insert(0, {"id": str(uuid.uuid4()), "term": term, "date": date.today().isoformat(), "difficulty": difficulty, "language": language})
            session["last_success"] = result["explanation"]
            session["last_error"] = ""
        except Exception as e:
            session["last_error"] = str(e)
            session["last_success"] = ""
        session.modified = True
        return redirect(url_for("home"))

    return render_template(
        "index.html",
        success_message=session.pop("last_success", ""),
        error_message=session.pop("last_error", ""),
        history=group_history(session["history"]),
        trending=TRENDING_CONCEPTS
    )


@app.route("/delete/<item_id>", methods=["DELETE"])
def delete_history(item_id):
    session["history"] = [h for h in session.get("history", []) if h["id"] != item_id]
    session.modified = True
    return ("", 204)


@app.route("/rename/<item_id>", methods=["POST"])
def rename_history(item_id):
    new_name = request.form.get("new_name", "").strip()
    if not new_name:
        return ("", 400)
    for item in session.get("history", []):
        if item["id"] == item_id:
            item["term"] = new_name
            break
    session.modified = True
    return ("", 204)


@app.route("/api/explain", methods=["POST"])
def api_explain():
    if not request.is_json:
        return jsonify({"status": "error", "message": "JSON required"}), 400

    data       = request.get_json()
    term       = data.get("term", "").strip()
    difficulty = data.get("difficulty", "intermediate")
    language   = data.get("language", "English")

    if not term:
        return jsonify({"status": "error", "message": "Term is required"}), 400
    if difficulty not in ("beginner", "intermediate", "expert"):
        difficulty = "intermediate"

    try:
        result = generate_explanation(term, difficulty, language)

        if "history" not in session:
            session["history"] = []
        session["history"] = [h for h in session["history"] if h["term"].lower() != term.lower()]
        session["history"].insert(0, {"id": str(uuid.uuid4()), "term": term, "date": date.today().isoformat(), "difficulty": difficulty, "language": language})
        session.modified = True

        related_terms = generate_related_terms(term)
        grouped       = group_history(session["history"])

        return jsonify({
            "status":        "success",
            "term":          term,
            "difficulty":    difficulty,
            "language":      language,
            "tag":           result["tag"],
            "explanation":   result["explanation"],
            "example":       result["example"],
            "key_insight":   result["key_insight"],
            "related_terms": related_terms,
            "history":       grouped
        })

    except Exception as e:
        print("API ERROR:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/followup", methods=["POST"])
def api_followup():
    if not request.is_json:
        return jsonify({"status": "error"}), 400
    data       = request.get_json()
    term       = data.get("term", "").strip()
    question   = data.get("question", "").strip()
    difficulty = data.get("difficulty", "intermediate")
    language   = data.get("language", "English")
    context    = data.get("context", "")
    if not term or not question:
        return jsonify({"status": "error", "message": "Term and question required"}), 400
    try:
        answer = generate_followup_answer(term, question, difficulty, context, language)
        return jsonify({"status": "success", "answer": answer})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    if not request.is_json:
        return jsonify({"status": "error"}), 400
    data = request.get_json()
    print(f"FEEDBACK: term={data.get('term')}, rating={data.get('rating')}")
    return jsonify({"status": "success"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)