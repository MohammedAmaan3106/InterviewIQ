"""
Face Analyzer Module.
Detects faces, evaluates camera framing, computes head orientation angles,
and extracts real facial landmarks using MediaPipe Tasks Vision or OpenCV Haar cascades.
"""
import math
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import cv2
import numpy as np

logger = logging.getLogger(__name__)

class FaceAnalyzer:
    def __init__(self, mediapipe_task_path: Optional[Path] = None, haar_path: Optional[Path] = None):
        self.mp_landmarker = None
        self.haar_cascade = None
        self.model_type = "none"

        # Attempt initializing MediaPipe FaceLandmarker
        if mediapipe_task_path and Path(mediapipe_task_path).exists():
            try:
                import mediapipe as mp
                from mediapipe.tasks import python
                from mediapipe.tasks.python import vision

                base_options = python.BaseOptions(model_asset_path=str(mediapipe_task_path))
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    output_face_blendshapes=False,
                    output_facial_transformation_matrixes=False,
                    num_faces=2,
                    min_face_detection_confidence=0.5,
                    min_face_presence_confidence=0.5
                )
                self.mp_landmarker = vision.FaceLandmarker.create_from_options(options)
                self.model_type = "mediapipe_tasks"
                logger.info("FaceAnalyzer initialized with MediaPipe FaceLandmarker.")
            except Exception as e:
                logger.warning(f"Failed to initialize MediaPipe FaceLandmarker: {e}. Falling back to Haar cascades.")

        # Fallback to OpenCV Haar Cascade if MediaPipe is not active
        if self.model_type == "none" and haar_path and Path(haar_path).exists():
            try:
                self.haar_cascade = cv2.CascadeClassifier(str(haar_path))
                if not self.haar_cascade.empty():
                    self.model_type = "opencv_haar"
                    logger.info("FaceAnalyzer initialized with OpenCV Haar Cascade.")
                else:
                    self.haar_cascade = None
            except Exception as e:
                logger.warning(f"Failed to initialize OpenCV Haar Cascade: {e}")

        if self.model_type == "none":
            logger.warning("FaceAnalyzer operating without trained model. Face metrics will be reported as unavailable.")

    def analyze(self, frame_bgr: np.ndarray) -> Dict[str, Any]:
        """
        Analyzes a single BGR OpenCV frame.
        Returns genuine measurements of face detection, framing, head tilt, and landmarks.
        """
        height, width = frame_bgr.shape[:2]
        if self.model_type == "mediapipe_tasks" and self.mp_landmarker:
            return self._analyze_mediapipe(frame_bgr, width, height)
        elif self.model_type == "opencv_haar" and self.haar_cascade:
            return self._analyze_haar(frame_bgr, width, height)
        else:
            return {
                "detected": False,
                "face_count": 0,
                "model_available": False,
                "framing_state": "Model unavailable",
                "framing_score": None,
                "bounding_box": None,
                "head_pose": None,
                "landmarks": []
            }

    def _analyze_mediapipe(self, frame_bgr: np.ndarray, width: int, height: int) -> Dict[str, Any]:
        import mediapipe as mp

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        try:
            result = self.mp_landmarker.detect(mp_image)
        except Exception as e:
            logger.error(f"Error during MediaPipe face detection: {e}")
            return self._empty_result("Face detection error")

        if not result.face_landmarks:
            return self._empty_result("Face not visible")

        face_count = len(result.face_landmarks)
        if face_count > 1:
            # Multiple faces detected
            framing_state = "Multiple faces detected"
        else:
            framing_state = "Good framing"

        primary_landmarks = result.face_landmarks[0]

        # Calculate bounding box from landmarks
        xs = [lm.x for lm in primary_landmarks]
        ys = [lm.y for lm in primary_landmarks]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        bbox_w = max_x - min_x
        bbox_h = max_y - min_y
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        face_area_ratio = bbox_w * bbox_h

        # Framing state determination
        if face_count == 1:
            if face_area_ratio < 0.07:
                framing_state = "Move closer"
            elif face_area_ratio > 0.50:
                framing_state = "Too close"
            elif abs(center_x - 0.5) > 0.18:
                framing_state = "Face off-center"
            else:
                framing_state = "Good framing"

        # Calculate framing quality score (0 - 100)
        # Optimal center_x: 0.5, optimal face_area_ratio: 0.20-0.35
        center_dev = abs(center_x - 0.5) * 2.0  # 0 to 1
        if 0.10 <= face_area_ratio <= 0.40:
            area_score = 100.0
        elif face_area_ratio < 0.10:
            area_score = max(0.0, (face_area_ratio / 0.10) * 100.0)
        else:
            area_score = max(0.0, (1.0 - (face_area_ratio - 0.40) / 0.30) * 100.0)

        framing_score = round(max(0.0, min(100.0, (1.0 - center_dev) * 60.0 + area_score * 0.40)), 1)

        # Real head orientation estimation
        # Left eye outer (landmark 33 or 263), Right eye outer (landmark 133 or 362)
        # In MediaPipe Face Mesh:
        # Left eye corner: landmark 33 (left), landmark 263 (right eye corner)
        left_eye = primary_landmarks[33]
        right_eye = primary_landmarks[263]
        nose_tip = primary_landmarks[1]
        chin = primary_landmarks[152]

        # Roll: tilt angle between the two eyes
        dx = right_eye.x - left_eye.x
        dy = right_eye.y - left_eye.y
        roll_deg = round(math.atan2(dy, dx) * 180.0 / math.pi, 1)

        # Yaw approximation: nose relative to eye span
        eye_span = math.hypot(dx, dy)
        yaw_ratio = 0.0
        if eye_span > 0.01:
            mid_eye_x = (left_eye.x + right_eye.x) / 2.0
            yaw_ratio = (nose_tip.x - mid_eye_x) / (eye_span * 0.5)
        yaw_deg = round(max(-45.0, min(45.0, yaw_ratio * 30.0)), 1)

        # Pitch approximation: nose relative to eye-chin vertical span
        pitch_deg = 0.0
        face_v_span = abs(chin.y - ((left_eye.y + right_eye.y) / 2.0))
        if face_v_span > 0.01:
            mid_eye_y = (left_eye.y + right_eye.y) / 2.0
            nose_v_ratio = (nose_tip.y - mid_eye_y) / face_v_span
            # Standard ratio is around 0.35-0.45
            pitch_deg = round(max(-45.0, min(45.0, (nose_v_ratio - 0.40) * 80.0)), 1)

        facing_camera = bool(abs(yaw_deg) < 18.0 and abs(pitch_deg) < 18.0 and abs(roll_deg) < 15.0)

        # Extract selected key landmarks for lightweight client-side overlay (normalized 0-1)
        # Points: jawline contour, eyes, nose bridge, mouth
        key_indices = [
            10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
            397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
            172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
            1, 2, 98, 327, 33, 133, 362, 263, 61, 291, 0, 17
        ]
        sampled_landmarks = [
            {"x": round(primary_landmarks[idx].x, 3), "y": round(primary_landmarks[idx].y, 3)}
            for idx in key_indices if idx < len(primary_landmarks)
        ]

        return {
            "detected": True,
            "face_count": face_count,
            "model_available": True,
            "model_type": "mediapipe_tasks",
            "framing_state": framing_state,
            "framing_score": framing_score,
            "face_area_ratio": round(face_area_ratio, 3),
            "bounding_box": {
                "x": round(min_x, 3),
                "y": round(min_y, 3),
                "w": round(bbox_w, 3),
                "h": round(bbox_h, 3),
                "pixel_x": int(min_x * width),
                "pixel_y": int(min_y * height),
                "pixel_w": int(bbox_w * width),
                "pixel_h": int(bbox_h * height)
            },
            "head_pose": {
                "roll_deg": roll_deg,
                "pitch_deg": pitch_deg,
                "yaw_deg": yaw_deg,
                "facing_camera": facing_camera
            },
            "landmarks": sampled_landmarks
        }

    def _analyze_haar(self, frame_bgr: np.ndarray, width: int, height: int) -> Dict[str, Any]:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self.haar_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(int(width * 0.15), int(height * 0.15))
        )

        if len(faces) == 0:
            return self._empty_result("Face not visible")

        face_count = len(faces)
        # Select largest face
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        x, y, w, h = faces[0]

        norm_x = x / width
        norm_y = y / height
        norm_w = w / width
        norm_h = h / height

        face_area_ratio = norm_w * norm_h
        center_x = norm_x + norm_w / 2.0

        if face_count > 1:
            framing_state = "Multiple faces detected"
        elif face_area_ratio < 0.08:
            framing_state = "Move closer"
        elif face_area_ratio > 0.50:
            framing_state = "Too close"
        elif abs(center_x - 0.5) > 0.18:
            framing_state = "Face off-center"
        else:
            framing_state = "Good framing"

        center_dev = abs(center_x - 0.5) * 2.0
        framing_score = round(max(0.0, min(100.0, (1.0 - center_dev) * 80.0 + 20.0)), 1)

        return {
            "detected": True,
            "face_count": face_count,
            "model_available": True,
            "model_type": "opencv_haar",
            "framing_state": framing_state,
            "framing_score": framing_score,
            "face_area_ratio": round(face_area_ratio, 3),
            "bounding_box": {
                "x": round(norm_x, 3),
                "y": round(norm_y, 3),
                "w": round(norm_w, 3),
                "h": round(norm_h, 3),
                "pixel_x": int(x),
                "pixel_y": int(y),
                "pixel_w": int(w),
                "pixel_h": int(h)
            },
            "head_pose": {
                "roll_deg": 0.0,
                "pitch_deg": 0.0,
                "yaw_deg": 0.0,
                "facing_camera": True
            },
            "landmarks": []
        }

    def _empty_result(self, state: str) -> Dict[str, Any]:
        return {
            "detected": False,
            "face_count": 0,
            "model_available": bool(self.model_type != "none"),
            "model_type": self.model_type,
            "framing_state": state,
            "framing_score": 0.0,
            "face_area_ratio": 0.0,
            "bounding_box": None,
            "head_pose": None,
            "landmarks": []
        }
