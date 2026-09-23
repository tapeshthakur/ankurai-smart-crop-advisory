from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.disease_service import analyse_leaf_image
from utils.auth import role_required


disease_bp = Blueprint("disease_bp", __name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


@disease_bp.route("/api/disease/detect", methods=["POST"])
@role_required("farmer", "admin")
def detect_disease_route():
    """Detect likely leaf disease from an uploaded image."""
    file = request.files.get("file")
    if file is None:
        return jsonify({"error": "Please upload a leaf image using the 'file' field."}), 400

    if _extension(file.filename or "") not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Only JPG, JPEG, and PNG leaf images are allowed."}), 400

    image_bytes = file.read()
    if not image_bytes:
        return jsonify({"error": "Uploaded image is empty."}), 400

    if len(image_bytes) > MAX_IMAGE_BYTES:
        return jsonify({"error": "Image size must be 5 MB or less."}), 400

    try:
        result = analyse_leaf_image(image_bytes, crop_context=request.form.get("crop", "").strip().lower())
        return jsonify({"result": result}), 200
    except Exception:
        return jsonify({"error": "Could not analyse this image. Please upload a clear leaf photo."}), 400
