# camera/capture_frame.py
# ========================
# צילום תמונה מהמצלמה של ה-Raspberry Pi.
# הקובץ הזה לא השתנה הרבה מהמקור שלך — הוא עבד טוב.

from picamera2 import Picamera2
import cv2
from config import CAMERA_RESOLUTION


def init_camera():
    """מאתחל את המצלמה ומחזיר את האובייקט שלה."""
    picam2 = Picamera2()
    config = picam2.create_still_configuration(
        main={"size": CAMERA_RESOLUTION}
    )
    picam2.configure(config)
    picam2.start()
    return picam2


def capture_frame(picam2):
    """מצלם תמונה אחת ומחזיר אותה בפורמט BGR (שזה מה ש-OpenCV עובד איתו)."""
    frame = picam2.capture_array()
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    return frame_bgr


if __name__ == "__main__":
    # אפשר להריץ את הקובץ הזה בנפרד לבדיקה:
    #   python -m camera.capture_frame
    picam2 = init_camera()
    frame = capture_frame(picam2)
    cv2.imwrite("test_frame.jpg", frame)
    picam2.stop()
    print(f"Image saved! Size: {frame.shape}")
