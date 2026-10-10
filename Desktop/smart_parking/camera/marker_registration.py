import cv2
import numpy as np
import json
import os


class MarkerRegistration:
    def __init__(self, reference_path=None):
        if reference_path is None:
            reference_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data", "reference_markers.json"
            )
        with open(reference_path) as f:
            ref_data = json.load(f)
        self.ref_points = {}
        for marker_id, corners in ref_data.items():
            self.ref_points[int(marker_id)] = np.array(corners, dtype=np.float32)
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        parameters = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
        print(f"[Registration] Loaded reference with markers: {list(self.ref_points.keys())}")

    def _bilinear_transform(self, src_pts, dst_pts):
        m1c, m1r = src_pts[0]
        m2c, m2r = src_pts[1]
        m3c, m3r = src_pts[2]
        m4c, m4r = src_pts[3]
        s1c, s1r = dst_pts[0]
        s2c, s2r = dst_pts[1]
        s3c, s3r = dst_pts[2]
        s4c, s4r = dst_pts[3]
        A = np.array([
            [1, m1c, m1r, m1c*m1r],
            [1, m2c, m2r, m2c*m2r],
            [1, m3c, m3r, m3c*m3r],
            [1, m4c, m4r, m4c*m4r]
        ], dtype=np.float64)
        bx = np.array([s1c, s2c, s3c, s4c], dtype=np.float64)
        by = np.array([s1r, s2r, s3r, s4r], dtype=np.float64)
        ax = np.linalg.solve(A, bx)
        ay = np.linalg.solve(A, by)
        return ax, ay

    def correct_frame(self, frame):
        corners, ids, _ = self.detector.detectMarkers(frame)
        if ids is None or len(ids) < 3:
            found = 0 if ids is None else len(ids)
            print(f"[Registration] Warning: found only {found}/4 markers, using raw frame")
            return frame, False
        src_points = []
        dst_points = []
        for i, marker_id in enumerate(ids):
            mid = int(marker_id[0])
            if mid in self.ref_points:
                src_center = np.mean(corners[i][0], axis=0)
                dst_center = np.mean(self.ref_points[mid], axis=0)
                src_points.append(src_center)
                dst_points.append(dst_center)
        if len(src_points) < 3:
            print("[Registration] Warning: not enough matching markers")
            return frame, False
        src_pts = np.array(src_points, dtype=np.float32)
        dst_pts = np.array(dst_points, dtype=np.float32)

        h, w = frame.shape[:2]
        if len(src_points) >= 4:
            ax, ay = self._bilinear_transform(src_pts[:4], dst_pts[:4])
            cols, rows = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
            map_x = (ax[0] + ax[1]*cols + ax[2]*rows + ax[3]*cols*rows).astype(np.float32)
            map_y = (ay[0] + ay[1]*cols + ay[2]*rows + ay[3]*cols*rows).astype(np.float32)
            corrected = cv2.remap(frame, map_x, map_y, cv2.INTER_LINEAR)
        else:
            M = cv2.getAffineTransform(src_pts[:3], dst_pts[:3])
            corrected = cv2.warpAffine(frame, M, (w, h))
        return corrected, True
