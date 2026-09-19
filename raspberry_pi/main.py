import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, make_response, request, send_file

from camera import CameraController
from config import CAMERA_MODEL, CAPTURE_DIR, HOST, PORT

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)
app = Flask(__name__)
camera = CameraController(CAMERA_MODEL)
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\.jpg$", re.IGNORECASE)


def cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.after_request
def add_cors(response):
    return cors(response)


@app.get("/api/status")
def status():
    state = camera.status()
    return jsonify({
        "camera_connected": state.connected,
        "camera_model": state.model,
        "resolution": {"width": state.width, "height": state.height},
        "ready": state.ready,
        "error": state.error,
    })


@app.post("/api/capture")
def capture():
    body = request.get_json(silent=True) or {}
    filename = body.get("filename") or f"IMG_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    if not SAFE_FILENAME.fullmatch(filename):
        return jsonify({"success": False, "error": "Filename must be a safe .jpg name"}), 400

    try:
        payload, width, height = camera.capture_jpeg()
    except Exception as exc:
        LOGGER.exception("Capture failed")
        return jsonify({"success": False, "error": str(exc)}), 503

    capture_id = hashlib.sha256(payload).hexdigest()
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    capture_path = CAPTURE_DIR / f"{capture_id}.jpg"
    capture_path.write_bytes(payload)
    LOGGER.info("Capture ready for transfer: %s", capture_path.name)

    response = make_response(payload)
    response.headers["Content-Type"] = "image/jpeg"
    response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    response.headers["X-Capture-Id"] = capture_id
    response.headers["X-Capture-Width"] = str(width)
    response.headers["X-Capture-Height"] = str(height)
    response.headers["X-Capture-Sha256"] = hashlib.sha256(payload).hexdigest()
    response.headers["Content-Length"] = str(len(payload))
    return response


@app.get("/api/capture/<capture_id>.jpg")
def download_capture(capture_id: str):
    if not re.fullmatch(r"[a-f0-9]{64}", capture_id):
        return jsonify({"error": "Invalid capture id"}), 400
    path = CAPTURE_DIR / f"{capture_id}.jpg"
    if not path.is_file():
        return jsonify({"error": "Capture not found"}), 404
    return send_file(path, mimetype="image/jpeg", max_age=0)


if __name__ == "__main__":
    camera.initialize()
    app.run(host=HOST, port=PORT, threaded=True)
