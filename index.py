import hmac
import os

from flask import Flask, jsonify, request

from main import LoginServiceError, perform_login

app = Flask(__name__)


@app.get("/")
def health():
    return jsonify({
        "status": "ok",
        "service": "VINOX Login API",
        "usage": {
            "GET": "/api/login?uid=...&password=...&key=...",
            "POST": "/api/login with JSON fields uid and password",
        },
    })


@app.route("/api/login", methods=["GET", "POST"])
def login():
    expected_key = os.environ.get("API_SECRET")
    if not expected_key:
        return jsonify({"ok": False, "error": "Server API_SECRET is not configured."}), 503

    if request.method == "GET":
        # WARNING: Query-string credentials and API keys can appear in browser
        # history, server logs, analytics, and referrer data. Prefer POST.
        data = request.args
        supplied_key = data.get("key", "")
    else:
        data = request.get_json(silent=True)
        supplied_key = request.headers.get("X-API-Key", "")
        if not isinstance(data, dict):
            return jsonify({"ok": False, "error": "Request body must be valid JSON."}), 400

    if not hmac.compare_digest(supplied_key, expected_key):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    uid = str(data.get("uid", "")).strip()
    password = str(data.get("password", "")).strip()
    if not uid.isdigit() or not password:
        return jsonify({"ok": False, "error": "Both numeric uid and password are required."}), 400

    try:
        result = perform_login(uid, password)
        return jsonify({"ok": True, "data": result}), 200
    except LoginServiceError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502
    except Exception:
        app.logger.exception("Unhandled login API error")
        return jsonify({"ok": False, "error": "Internal server error."}), 500
