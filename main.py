import cv2
from utils import decode_codes_silent, init_camera


def draw_barcode(img, barcode, color=(255, 0, 255)):
    import numpy as np
    data = barcode.data.decode("utf-8")
    pts = np.array([barcode.polygon], np.int32).reshape((-1, 1, 2))
    cv2.polylines(img, [pts], True, color, 4)
    x, y, w, h = barcode.rect
    cv2.putText(img, data, (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    return data


def show_frame(img, window_name="Result"):
    cv2.imshow(window_name, img)


def cleanup(cap):
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    cap = init_camera()
    while True:
        success, img = cap.read()
        if not success:
            print("Camera not working!")
            break
        for bc in decode_codes_silent(img):
            data = draw_barcode(img, bc)
            print("Scanned:", data)
        show_frame(img)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cleanup(cap)
