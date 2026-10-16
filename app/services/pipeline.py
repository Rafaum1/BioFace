from pathlib import Path

import cv2
import face_recognition
import numpy as np

from app.services.preprocessing import preprocess_bgr


class RecognitionPipeline:
    """Executa e registra cada etapa da identificação facial 1:N."""

    def __init__(self, repository, tolerance):
        self.repository = repository
        self.tolerance = tolerance

    @staticmethod
    def _write(path: Path, image):
        if not cv2.imwrite(str(path), image):
            raise OSError(f"Não foi possível salvar a imagem intermediária: {path.name}")

    def authenticate(self, image_bytes, output_dir: Path):
        output_dir.mkdir(parents=True, exist_ok=True)
        steps = []

        # 1. Aquisição: decodifica e preserva a imagem original recebida da webcam.
        raw = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if raw is None:
            return {
                "status": "error",
                "message": "Não foi possível abrir a imagem capturada.",
                "steps": [{"name": "Aquisição", "detail": "O arquivo recebido não é uma imagem válida."}],
                "images": False,
                "candidates": [],
            }
        self._write(output_dir / "01_original.jpg", raw)
        height, width = raw.shape[:2]
        steps.append({"name": "Aquisição", "detail": f"Imagem recebida: {width} × {height} pixels."})

        # 2. Pré-processamento igual também às imagens de referência da base.
        processed_bgr = preprocess_bgr(raw)
        self._write(output_dir / "02_preprocessada.jpg", processed_bgr)
        processed_rgb = cv2.cvtColor(processed_bgr, cv2.COLOR_BGR2RGB)
        steps.append({
            "name": "Pré-processamento",
            "detail": (
                "Aplicada a técnica de filtragem espacial pelo filtro bilateral "
                "(d=5, sigmaColor=25, sigmaSpace=25) e a técnica de melhoria de contraste pelo CLAHE "
                "no canal de luminosidade. "
                f"Redimensionamento para {processed_bgr.shape[1]} × {processed_bgr.shape[0]} quando necessário."
            ),
        })

        # 3. Detecção e segmentação: localiza uma face e recorta sua região.
        locations = face_recognition.face_locations(processed_rgb, model="hog")
        annotated = processed_bgr.copy()
        for top, right, bottom, left in locations:
            cv2.rectangle(annotated, (left, top), (right, bottom), (38, 190, 120), 3)
        self._write(output_dir / "03_rosto_detectado.jpg", annotated)
        steps.append({"name": "Detecção/segmentação", "detail": f"{len(locations)} face(s) detectada(s); o sistema exige exatamente uma."})

        if len(locations) != 1:
            message = (
                "Não encontramos um rosto. Tente outra foto com o rosto bem iluminado."
                if len(locations) == 0
                else "A foto precisa mostrar apenas uma pessoa. Selecione outra imagem."
            )
            return {
                "status": "error",
                "message": message,
                "steps": steps,
                "images": True,
                "candidates": [],
            }

        top, right, bottom, left = locations[0]
        face_crop = processed_bgr[max(0, top):bottom, max(0, left):right]
        if face_crop.size:
            self._write(output_dir / "04_rosto_segmentado.jpg", face_crop)
        steps[-1]["detail"] += " A região delimitada foi salva como recorte facial."

        # 4. Extração de características: embedding de 128 dimensões.
        encodings = face_recognition.face_encodings(processed_rgb, locations)
        if not encodings:
            return {
                "status": "error",
                "message": "Não conseguimos analisar o rosto. Tente uma foto mais nítida, olhando para a câmera.",
                "steps": steps,
                "images": True,
                "candidates": [],
            }
        encoding = encodings[0]
        sample = [round(float(value), 4) for value in encoding[:8]]
        steps.append({
            "name": "Extração de características",
            "detail": f"Embedding numérico de {len(encoding)} dimensões calculado pelo dlib.",
        })

        # 5. Comparação 1:N contra todos os usuários ativos e suas imagens cadastradas.
        known = self.repository.known_faces()
        if not known:
            steps.append({"name": "Comparação 1:N", "detail": "Não há imagens faciais cadastradas para comparar."})
            return {
                "status": "error",
                "message": "Nenhum perfil facial está disponível. Faça um cadastro antes de continuar.",
                "steps": steps,
                "images": True,
                "encoding_size": len(encoding),
                "encoding_sample": sample,
                "candidates": [],
                "tolerance": self.tolerance,
            }

        distances = face_recognition.face_distance([item["encoding"] for item in known], encoding)
        best_by_user = {}
        for item, distance in zip(known, distances):
            user = item["user"]
            user_id = user["id"]
            distance = float(distance)
            if user_id not in best_by_user or distance < best_by_user[user_id]["distance_raw"]:
                best_by_user[user_id] = {"user": user, "distance_raw": distance}

        ranked = sorted(best_by_user.values(), key=lambda item: item["distance_raw"])
        recognized = ranked[0]["distance_raw"] <= self.tolerance
        candidates = [
            {"user": item["user"], "distance": round(item["distance_raw"], 4), "accepted": item["distance_raw"] <= self.tolerance}
            for item in ranked
        ]
        steps.append({
            "name": "Comparação 1:N",
            "detail": f"Consultados {len(candidates)} perfil(is). Limite de correspondência aplicado: {self.tolerance:.2f}.",
        })

        # 6. Decisão: o menor valor de distância só é aceito se estiver dentro do limiar.
        steps.append({
            "name": "Tomada de decisão",
            "detail": "Identidade confirmada." if recognized else "Não houve correspondência suficiente.",
        })
        result = {
            "status": "success" if recognized else "unknown",
            "message": "Identidade confirmada." if recognized else "Não encontramos um perfil compatível.",
            "steps": steps,
            "images": True,
            "encoding_size": len(encoding),
            "encoding_sample": sample,
            "candidates": candidates,
            "tolerance": self.tolerance,
        }
        if recognized:
            result["user"] = ranked[0]["user"]
        return result
