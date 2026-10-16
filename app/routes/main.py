import base64
import binascii
import io
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, url_for
import qrcode
from werkzeug.datastructures import FileStorage

from app.network import get_lan_ip
from app.services.pipeline import RecognitionPipeline
from app.services.repository import UserRepository

bp = Blueprint("main", __name__)


def repository():
    return UserRepository(current_app.config["DATA_DIR"])


def pipeline():
    return RecognitionPipeline(repository(), current_app.config["MATCH_TOLERANCE"])


def mobile_registration_link():
    parsed = urlsplit(request.host_url)
    hostname = parsed.hostname or "127.0.0.1"
    if hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        hostname = get_lan_ip()
    formatted_host = f"[{hostname}]" if ":" in hostname else hostname
    netloc = f"{formatted_host}:{parsed.port}" if parsed.port else formatted_host
    return urlunsplit((parsed.scheme, netloc, url_for("main.index"), "", ""))


def qr_data_uri(value):
    image = qrcode.make(value)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@bp.get("/")
def index():
    users = [user for user in repository().list_users() if user.get("active", True)]
    mobile_url = mobile_registration_link()
    return render_template("index.html", users=users, mobile_url=mobile_url, mobile_qr=qr_data_uri(mobile_url))


@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        access_level = request.form.get("access_level", "")
        images = request.files.getlist("images")
        camera_image = request.form.get("camera_image", "")
        if camera_image:
            match = re.fullmatch(r"data:(image/(?:jpeg|png));base64,([A-Za-z0-9+/]+={0,2})", camera_image)
            if not match:
                flash("A imagem capturada pela webcam é inválida.", "error")
                return redirect(url_for("main.cadastro"))
            try:
                image_bytes = base64.b64decode(match.group(2), validate=True)
            except (binascii.Error, ValueError):
                flash("Não foi possível ler a foto capturada. Tente novamente.", "error")
                return redirect(url_for("main.cadastro"))
            if not image_bytes or len(image_bytes) > 4 * 1024 * 1024:
                flash("A foto da webcam excede o limite de 4 MB. Capture novamente.", "error")
                return redirect(url_for("main.cadastro"))
            extension = "jpg" if match.group(1) == "image/jpeg" else "png"
            images.append(FileStorage(stream=io.BytesIO(image_bytes), filename=f"webcam.{extension}", content_type=match.group(1)))
        if not name or access_level not in {"1", "2", "3"} or not any(image.filename for image in images):
            flash("Informe nome, nível de acesso e ao menos uma imagem.", "error")
            return redirect(url_for("main.cadastro"))
        try:
            user = repository().add_user(name, int(access_level), images)
            flash(f"{user['name']} foi cadastrado com sucesso.", "success")
            return redirect(url_for("main.cadastro"))
        except ValueError as error:
            flash(str(error), "error")
    return render_template("cadastro.html")


@bp.post("/autenticar")
def autenticar():
    image_data = request.form.get("image_data", "")
    if not image_data.startswith("data:image/") or "," not in image_data:
        flash("Capture uma imagem pela webcam antes de autenticar.", "error")
        return redirect(url_for("main.index"))
    try:
        image_bytes = base64.b64decode(image_data.split(",", 1)[1], validate=True)
    except (binascii.Error, ValueError):
        flash("A imagem capturada é inválida.", "error")
        return redirect(url_for("main.index"))

    capture_id = uuid4().hex
    result_dir = current_app.config["CAPTURES_DIR"] / capture_id
    result = pipeline().authenticate(image_bytes, result_dir)
    with (result_dir / "result.json").open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    return render_template("resultado.html", result=result, capture_id=capture_id)


@bp.get("/processamento/<capture_id>")
def processamento(capture_id):
    if not capture_id.isalnum():
        return "Captura inválida", 404
    result_dir = current_app.config["CAPTURES_DIR"] / capture_id
    result_file = result_dir / "result.json"
    if not result_file.exists():
        return "Processamento não encontrado", 404
    with result_file.open(encoding="utf-8") as file:
        result = json.load(file)
    return render_template("processamento.html", capture_id=capture_id, result=result)


@bp.get("/capturas/<capture_id>/<path:filename>")
def capture_file(capture_id, filename):
    if not capture_id.isalnum():
        return "Captura inválida", 404
    return send_from_directory(Path(current_app.config["CAPTURES_DIR"]) / capture_id, filename)
