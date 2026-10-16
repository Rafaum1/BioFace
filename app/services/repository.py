import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4

import face_recognition
import cv2

from app.services.preprocessing import preprocess_bgr


class UserRepository:
    """Le e atualiza o JSON de usuarios e as imagens faciais cadastradas."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.faces_dir = self.data_dir / "faces"
        self.users_file = self.data_dir / "users.json"
        self.faces_dir.mkdir(parents=True, exist_ok=True)
        if not self.users_file.exists():
            self._save({"users": []})

    def _load(self):
        if not self.users_file.exists():
            data = {"users": []}
            self._save(data)
            return data

        content = self.users_file.read_text(encoding="utf-8")
        if not content.strip():
            # An empty database is safe to initialize only if no biometric folders exist.
            if any(self.faces_dir.iterdir()):
                raise ValueError("users.json está vazio, mas há imagens cadastradas em data/faces. Restaure um backup antes de continuar.")
            data = {"users": []}
            self._save(data)
            return data

        try:
            data = json.loads(content)
        except json.JSONDecodeError as error:
            raise ValueError(f"users.json contém JSON inválido na linha {error.lineno}, coluna {error.colno}.") from error
        if not isinstance(data, dict) or not isinstance(data.get("users"), list):
            raise ValueError('users.json deve conter um objeto com a lista "users".')
        return data

    def _save(self, data):
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.users_file.parent,
                suffix=".tmp",
                delete=False,
            ) as file:
                temporary_path = Path(file.name)
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.users_file)
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()

    def list_users(self):
        return self._load()["users"]

    def add_user(self, name, access_level, uploads):
        user_id = f"usr_{uuid4().hex[:10]}"
        user_dir = self.faces_dir / user_id
        user_dir.mkdir()
        paths = []

        for index, upload in enumerate(uploads):
            if not upload.filename:
                continue
            suffix = Path(upload.filename).suffix.lower()
            if suffix not in {".jpg", ".jpeg", ".png"}:
                continue

            target = user_dir / f"{index + 1}{suffix}"
            upload.save(target)
            try:
                image = face_recognition.load_image_file(target)
                image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                image = cv2.cvtColor(preprocess_bgr(image_bgr), cv2.COLOR_BGR2RGB)
                face_count = len(face_recognition.face_encodings(image))
            except Exception:
                target.unlink(missing_ok=True)
                continue

            if face_count != 1:
                target.unlink(missing_ok=True)
                continue
            paths.append(str(target.relative_to(self.data_dir)).replace("\\", "/"))

        if not paths:
            user_dir.rmdir()
            raise ValueError("Nenhuma imagem válida com exatamente um rosto foi enviada.")

        user = {
            "id": user_id,
            "name": name,
            "access_level": access_level,
            "images": paths,
            "active": True,
        }
        data = self._load()
        data["users"].append(user)
        self._save(data)
        return user

    def known_faces(self):
        known = []
        for user in self.list_users():
            if not user.get("active", True):
                continue
            for relative_path in user.get("images", []):
                path = self.data_dir / relative_path
                if not path.exists():
                    continue
                try:
                    image = face_recognition.load_image_file(path)
                    image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                    image = cv2.cvtColor(preprocess_bgr(image_bgr), cv2.COLOR_BGR2RGB)
                    encodings = face_recognition.face_encodings(image)
                except Exception:
                    continue
                if encodings:
                    known.append({"user": user, "encoding": encodings[0]})
        return known
