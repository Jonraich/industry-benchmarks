"""
Industry Financial Benchmarks tool -- Flask API + static frontend server.

Run:
    export CENSUS_API_KEY=your_key_here
    pip install -r requirements.txt
    python app.py
Then open http://localhost:5000
"""
import os
from flask import Flask, jsonify, request, send_from_directory

from census_client import CensusAPIError
from naics_codes import search_naics
from states import STATE_NAMES
from report_builder import build_report

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
