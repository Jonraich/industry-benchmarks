"""
Industry Financial Benchmarks tool -- Flask API + static frontend server.

Run:
    export CENSUS_API_KEY=your_key_here
    pip install -r requirements.txt
    python app.py
Then open http://localhost:5000
"""
import os
import re
from flask import Flask, jsonify, request, send_from_directory

from census_client import CensusAPIError
from naics_codes import search_naics
from states import STATE_NAMES
from report_builder import build_report
from pdf_report import build_pdf
from email_sender import send_report_email, EmailSendError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _find_frontend_dir():
    """Locate the folder containing index.html, tolerating naming/casing
    differences (e.g. 'frontend' vs 'Frontend Folder') so this doesn't break
    just because a folder got renamed during upload to GitHub."""
    parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = ["frontend", "Frontend Folder", "Frontend", "front-end"]
    for name in candidates:
        path = os.path.join(parent, name)
        if os.path.isfile(os.path.join(path, "index.html")):
            return path
    # Fall back to scanning every sibling directory for index.html.
    for entry in os.listdir(parent):
        path = os.path.join(parent, entry)
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, "index.html")):
            return path
    raise FileNotFoundError(
        "Could not find a folder containing index.html next to the backend "
        "folder. Make sure your frontend files are in a sibling directory."
    )


FRONTEND_DIR = _find_frontend_dir()

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/api/states")
def states():
    return jsonify([{"code": k, "name": v} for k, v in sorted(STATE_NAMES.items(), key=lambda kv: kv[1])])


@app.get("/api/naics/search")
def naics_search():
    q = request.args.get("q", "")
    return jsonify([{"code": c, "label": label} for c, label in search_naics(q)])


@app.get("/api/report")
def report():
    naics = request.args.get("naics")
    state = request.args.get("state")
    api_key = request.args.get("key")  # optional override of CENSUS_API_KEY env var
    if not naics or not state:
        return jsonify({"error": "naics and state query params are required"}), 400
    try:
        data = build_report(naics, state, api_key=api_key)
    except CensusAPIError as e:
        return jsonify({"error": str(e)}), 502
    if "error" in data:
        return jsonify(data), 404
    return jsonify(data)


@app.post("/api/email-report")
def email_report():
    payload = request.get_json(silent=True) or {}
    naics = payload.get("naics")
    state = payload.get("state")
    email = (payload.get("email") or "").strip()
    api_key = payload.get("key")  # optional override of CENSUS_API_KEY env var

    if not naics or not state:
        return jsonify({"error": "naics and state are required"}), 400
    if not email or not EMAIL_RE.match(email):
        return jsonify({"error": "Please provide a valid email address."}), 400

    try:
        data = build_report(naics, state, api_key=api_key)
    except CensusAPIError as e:
        return jsonify({"error": str(e)}), 502
    if "error" in data:
        return jsonify(data), 404

    try:
        pdf_bytes = build_pdf(data)
    except Exception as e:
        return jsonify({"error": f"Could not build the PDF: {e}"}), 500

    try:
        send_report_email(
            email, pdf_bytes,
            data["industry"].get("naics_label", "Industry"),
            data["geography"]["state_name"],
        )
    except EmailSendError as e:
        return jsonify({"error": str(e)}), 502

    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
