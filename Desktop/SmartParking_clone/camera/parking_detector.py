# camera/parking_detector.py
# ===========================
# זיהוי חניות תפוסות/פנויות.
# מבוסס על הקוד הקיים שלך (analyze_parking_space.py)
# בשלב מאוחר יותר נוסיף כאן marker-based registration.

import cv2
import numpy as np
import os
import json
from config import FILL_RATIO_THRESHOLD, PARKING_SPACES_FILE


def load_parking_spaces(path=None):
    """טוען את קואורדינטות החניות מקובץ JSON.
    הקובץ נוצר עם generate_markers.py — כל חנייה = 4 נקודות.
    """
    if path is None:
        # מחפש את הקובץ ביחס לתיקיית הפרויקט הראשית
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            PARKING_SPACES_FILE
        )
    with open(path) as f:
        return json.load(f)


def preprocess_frame(frame_bgr):
    """מכין את התמונה לניתוח.
    
    מה קורה כאן צעד אחרי צעד:
    1. ממיר לגווני אפור (כי צבע לא חשוב לנו, רק בהירות)
    2. מטשטש קצת (להוריד רעשים)
    3. adaptive threshold — הופך את התמונה לשחור-לבן 
       כך שאזורים כהים (= רכב) נהיים לבנים
    4. morphological close — סוגר חורים קטנים בתוצאה
    """
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    adaptive = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        25, 5
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    clean = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel)
    return clean


def analyze_space_occupancy(spaces, clean_frame, threshold=None):
    """בודק כל חנייה — תפוסה או פנויה.
    
    הרעיון: לכל חנייה, סופרים כמה פיקסלים לבנים יש באזור שלה.
    אם היחס (fill ratio) גבוה מהסף — יש שם משהו = תפוס.
    אם היחס נמוך — ריק = פנוי.
    """
    if threshold is None:
        threshold = FILL_RATIO_THRESHOLD

    results = []
    for i, space in enumerate(spaces):
        # יוצר מסכה בצורת החנייה
        mask = np.zeros(clean_frame.shape, dtype=np.uint8)
        pts = np.array(space, dtype=np.int32)
        cv2.fillPoly(mask, [pts], 255)

        # מחשב כמה פיקסלים לבנים יש בתוך המסכה
        masked = cv2.bitwise_and(clean_frame, mask)
        white_pixels = cv2.countNonZero(masked)
        area = cv2.contourArea(pts)
        ratio = white_pixels / area if area > 0 else 0

        results.append({
            "index": i,
            "occupied": ratio > threshold,
            "status": "OCCUPIED" if ratio > threshold else "FREE",
            "ratio": ratio,
            "points": pts
        })
    return results


def get_free_count(results):
    """סופר כמה חניות פנויות."""
    return sum(1 for r in results if not r["occupied"])


def draw_results(frame, results):
    """מצייר על התמונה את התוצאות — ירוק=פנוי, אדום=תפוס.
    שימושי לדיבוג ולמסך המפעיל.
    """
    for r in results:
        color = (0, 0, 255) if r["occupied"] else (0, 255, 0)
        cv2.polylines(frame, [r["points"]], True, color, 3)
        mx = int(np.mean([p[0] for p in r["points"]]))
        my = int(np.mean([p[1] for p in r["points"]]))
        cv2.putText(
            frame, f"{r['index']}:{r['status']}",
            (mx - 40, my + 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
        )
    return frame
