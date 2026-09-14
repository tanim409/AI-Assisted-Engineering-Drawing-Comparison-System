import cv2
import numpy as np
from collections import Counter


def load_image_from_bytes(image_bytes: bytes) -> np.ndarray:
    """Decode image bytes (PNG/JPG/etc) to BGR numpy array."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")
    return img


def to_gray(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def denoise(gray: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(gray, h=5)


def enhance_contrast(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def binarize(gray: np.ndarray) -> np.ndarray:
    """Otsu's binarization - good default for line-drawing style content."""
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def deskew(gray: np.ndarray) -> np.ndarray:
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=150)
    if lines is None:
        return gray

    angles = []
    for line in lines:
        rho, theta = line[0]
        angle = np.degrees(theta) - 90
        angle = angle % 90
        if angle > 45:
            angle -= 90
        angles.append(round(angle, 0))

    dominant_angle = Counter(angles).most_common(1)[0][0]
    if abs(dominant_angle) < 0.5:
        return gray

    (h, w) = gray.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, dominant_angle, 1.0)
    return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def preprocess_pipeline(source) -> dict:
    """
    source: one of:
      - bytes: raw image bytes (PNG/JPG/etc) -> decoded and processed
      - np.ndarray: already-loaded BGR image array -> processed directly
    Returns dict with "color" (BGR), "gray", "binary"
    """
    if isinstance(source, bytes):
        color = load_image_from_bytes(source)
    elif isinstance(source, np.ndarray):
        color = source
    else:
        raise TypeError(f"preprocess_pipeline expects bytes or ndarray, got {type(source)}")
    gray = to_gray(color)
    gray = denoise(gray)
    gray = enhance_contrast(gray)
    gray = deskew(gray)
    binary = binarize(gray)
    return {"color": color, "gray": gray, "binary": binary}