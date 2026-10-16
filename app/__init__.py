from pathlib import Path
from flask import Flask
from werkzeug.exceptions import RequestEntityTooLarge


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    root = Path(app.root_path).parent
    app.config.update(
        SECRET_KEY="troque-esta-chave-em-producao",
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
        DATA_DIR=root / "data",
        CAPTURES_DIR=Path(app.instance_path) / "captures",
        MATCH_TOLERANCE=0.60,
    )
    app.config["DATA_DIR"].mkdir(parents=True, exist_ok=True)
    app.config["CAPTURES_DIR"].mkdir(parents=True, exist_ok=True)

    from .routes.main import bp
    app.register_blueprint(bp)

    @app.errorhandler(RequestEntityTooLarge)
    def request_too_large(_error):
        return (
            "A imagem enviada é grande demais. Capture novamente ou escolha uma foto menor (JPEG/PNG).",
            413,
        )

    return app
