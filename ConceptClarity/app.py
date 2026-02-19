from flask import Flask, render_template, request, session, redirect, url_for
from ai_explainer import generate_explanation
import uuid
from datetime import date, timedelta

app = Flask(__name__)
app.secret_key = "conceptclarity-secret-key"


# ---------- HELPER FUNCTION (NOT A ROUTE) ----------
def group_history(history):
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    grouped = {"Today": [], "Yesterday": [], "Earlier": []}

    for item in history:
        item_date = item.get("date")  # ✅ SAFE ACCESS

        if item_date == today:
            grouped["Today"].append(item)
        elif item_date == yesterday:
            grouped["Yesterday"].append(item)
        else:
            grouped["Earlier"].append(item)

    return grouped



# ---------- MAIN ROUTE ----------
@app.route("/", methods=["GET", "POST"])
def home():
    # Initialize history safely
    if "history" not in session:
        session["history"] = []

    # 🔧 Fix old history items (backward compatibility)
    for item in session["history"]:
        if "date" not in item:
            item["date"] = date.today().isoformat()

    # ---------- POST ----------
    if request.method == "POST":
        term = request.form.get("term", "").strip()

        try:
            explanation = generate_explanation(term)

            # Remove duplicates
            session["history"] = [
                h for h in session["history"]
                if h["term"].lower() != term.lower()
            ]

            # Insert new history item
            session["history"].insert(0, {
                "id": str(uuid.uuid4()),
                "term": term,
                "date": date.today().isoformat()
            })

            # Store explanation temporarily
            session["last_success"] = explanation
            session["last_error"] = ""

        except Exception as e:
            session["last_error"] = str(e)
            session["last_success"] = ""

        session.modified = True

        # ✅ IMPORTANT: redirect (PRG pattern)
        return redirect(url_for("home"))

    # ---------- GET ----------
    success_message = session.pop("last_success", "")
    error_message = session.pop("last_error", "")

    return render_template(
        "index.html",
        success_message=success_message,
        error_message=error_message,
        history=group_history(session["history"])
    )

# ---------- DELETE ----------
@app.route("/delete/<item_id>", methods=["DELETE"])
def delete_history(item_id):
    session["history"] = [
        h for h in session.get("history", [])
        if h["id"] != item_id
    ]
    session.modified = True
    return ("", 204)


# ---------- RENAME ----------
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


if __name__ == "__main__":
    app.run(debug=True)
