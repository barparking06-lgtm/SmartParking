import os
import cv2
import numpy as np

from camera.capture_frame import init_camera, capture_frame
from camera.marker_registration import MarkerRegistration
from camera.parking_detector import (
    load_parking_spaces,
    preprocess_frame,
    analyze_space_occupancy,
    draw_results,
    get_free_count
)

OUT_DIR = "data/rev2_images"
os.makedirs(OUT_DIR, exist_ok=True)

# 1. Capture current frame
picam2 = init_camera()
frame = capture_frame(picam2)
picam2.stop()

cv2.imwrite(os.path.join(OUT_DIR, "01_raw_frame.jpg"), frame)

# 2. Correct / align image using ArUco reference
registration = MarkerRegistration()
aligned_frame, ok = registration.correct_frame(frame)

cv2.imwrite(os.path.join(OUT_DIR, "02_aligned_frame.jpg"), aligned_frame)

# 3. Create binary processing image
binary = preprocess_frame(aligned_frame)
cv2.imwrite(os.path.join(OUT_DIR, "03_binary_threshold_mask.jpg"), binary)

# 4. Analyze parking spaces and draw final result
spaces = load_parking_spaces()
results = analyze_space_occupancy(spaces, binary)
final_img = draw_results(aligned_frame.copy(), results)

free_count = get_free_count(results)
status_text = f"[{'OK' if ok else 'RAW'}] Free: {free_count}/{len(results)}"
cv2.putText(final_img, status_text, (10, 35),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 2)

cv2.imwrite(os.path.join(OUT_DIR, "04_final_detection.jpg"), final_img)

# 5. Create one combined image for the report
def resize_to(img, width=600):
    h, w = img.shape[:2]
    scale = width / w
    return cv2.resize(img, (width, int(h * scale)))

raw_small = resize_to(frame)
aligned_small = resize_to(aligned_frame)
binary_bgr = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
binary_small = resize_to(binary_bgr)
final_small = resize_to(final_img)

def add_title(img, title):
    canvas = np.ones((img.shape[0] + 45, img.shape[1], 3), dtype=np.uint8) * 255
    canvas[45:, :, :] = img
    cv2.putText(canvas, title, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    return canvas

a = add_title(raw_small, "1. Raw camera frame")
b = add_title(aligned_small, "2. ArUco aligned frame")
c = add_title(binary_small, "3. Binary threshold mask")
d = add_title(final_small, "4. Final FREE / OCCUPIED result")

top = np.hstack([a, b])
bottom = np.hstack([c, d])
grid = np.vstack([top, bottom])

cv2.imwrite(os.path.join(OUT_DIR, "05_processing_steps_grid.jpg"), grid)

print("Saved REV2 processing images to:", OUT_DIR)
print("Use this image for the report:")
print(os.path.join(OUT_DIR, "05_processing_steps_grid.jpg"))
