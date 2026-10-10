import cv2
import numpy as np
import json
import os

SCALE = 0.5
points = []
spaces = []

ref_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reference_frame.jpg")
img_orig = cv2.imread(ref_path)

if img_orig is None:
    print("ERROR: Cannot load data/reference_frame.jpg")
    exit(1)

img_small = cv2.resize(img_orig, None, fx=SCALE, fy=SCALE)

def mouse_callback(event, x, y, flags, param):
    global points, spaces
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append([x, y])
        print(f"Point {len(points)}/4: ({x}, {y})")
        if len(points) == 4:
            spaces.append(points.copy())
            points.clear()

cv2.namedWindow("Mark Parking Spaces")
cv2.setMouseCallback("Mark Parking Spaces", mouse_callback)

print("=== Parking Space Marker ===")
print("Click 4 corners for each parking space")
print("Press u to undo last space")
print("Press s to save and exit")
print("Press q to quit without saving")

while True:
    display = img_small.copy()
    for i, space in enumerate(spaces):
        pts = np.array(space, dtype=np.int32)
        cv2.polylines(display, [pts], True, (0, 255, 0), 2)
        cx = int(np.mean([p[0] for p in space]))
        cy = int(np.mean([p[1] for p in space]))
        cv2.putText(display, str(i), (cx-10, cy+10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    for p in points:
        cv2.circle(display, (p[0], p[1]), 5, (0, 0, 255), -1)
    cv2.imshow("Mark Parking Spaces", display)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("s"):
        real_spaces = []
        for space in spaces:
            real_space = [[int(p[0]/SCALE), int(p[1]/SCALE)] for p in space]
            real_spaces.append(real_space)
        save_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 "data", "parking_spaces.json")
        with open(save_path, "w") as f:
            json.dump(real_spaces, f)
        print(f"Saved {len(spaces)} spaces to data/parking_spaces.json")
        break
    elif key == ord("u") and spaces:
        removed = spaces.pop()
        print(f"Removed last space. {len(spaces)} remaining")
    elif key == ord("q"):
        print("Quit without saving")
        break

cv2.destroyAllWindows()
