import cv2
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode
from PySide6.QtGui import QImage, QPixmap

def decode_codes_silent(frame):
    try:
        return decode(frame)
    except Exception:
        return []

def init_camera(camera_id=0, width=640, height=480):
    cap = cv2.VideoCapture(camera_id)
    cap.set(3, width)
    cap.set(4, height)
    return cap

def convert_1bit_to_rgb(img):
    pil_img = Image.new("RGB", img.size, (255, 255, 255))
    pil_img.paste(img, (0, 0))
    return pil_img

def pil_to_qpixmap(pil_img, width, height):
    preview = pil_img.resize((width, height), Image.Resampling.LANCZOS)
    data = preview.tobytes("raw", "RGB")
    qimg = QImage(data, width, height, width * 3, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg)
