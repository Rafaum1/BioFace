import cv2


def preprocess_bgr(image):
    """Padroniza tamanho, filtra ruído e realça contraste em uma imagem BGR."""
    height, width = image.shape[:2]
    scale = min(1.0, 900 / max(width, height))
    resized = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else image.copy()

    # Suaviza ruídos mantendo contornos faciais mais definidos que um blur gaussiano.
    filtered = cv2.bilateralFilter(resized, d=5, sigmaColor=25, sigmaSpace=25)

    # Equaliza o contraste local no canal de luminosidade sem equalizar diretamente as cores.
    lab = cv2.cvtColor(filtered, cv2.COLOR_BGR2LAB)
    lightness, channel_a, channel_b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    equalized = clahe.apply(lightness)
    return cv2.cvtColor(cv2.merge((equalized, channel_a, channel_b)), cv2.COLOR_LAB2BGR)
