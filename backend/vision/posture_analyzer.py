"""
Posture Analyzer Module.
Evaluates upper body posture, shoulder alignment, and presence using MediaPipe PoseLandmarker.
If shoulders are out of camera view or model is unavailable, reports 'Posture unavailable'.
"""
import math
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import cv2
import numpy as np

logger = logging.getLogger(__name__)

class PostureAnalyzer:
    def __init__(self, mediapipe_task_path: Optional[Path] = None):
        self.mp_landmarker = None
        self.model_available = False

        if mediapipe_task_path and Path(mediapipe_task_path).exists():
            try:
                import mediapipe as mp
                from mediapipe.tasks import python
                from mediapipe.tasks.python import vision

                base_options = python.BaseOptions(model_asset_path=str(mediapipe_task_path))
                options = vision.PoseLandmarkerOptions(
                    base_options=base_options,
                    output_segmentation_masks=False,
                    num_poses=1,
                    min_pose_detection_confidence=0.5,
                    min_pose_presence_confidence=0.5
                )
                self.mp_landmarker = vision.PoseLandmarker.create_from_options(options)
                self.model_available = True
                logger.info("PostureAnalyzer initialized with MediaPipe PoseLandmarker.")
            except Exception as e:
                logger.warning(f"Failed to initialize MediaPipe PoseLandmarker: {e}. Posture analysis will be marked unavailable.")

    def analyze(self, frame_bgr: np.ndarray) -> Dict[str, Any]:
        """
        Analyzes a single BGR OpenCV frame for posture and shoulder alignment.
        """
        if not self.model_available or not self.mp_landmarker:
            return {
                "detected": False,
                "model_available": False,
                "state": "Posture unavailable",
                "shoulder_tilt_deg": None,
                "shoulder_width_ratio": None,
                "posture_score": None,
                "landmarks": None
            }

        height, width = frame_bgr.shape[:2]
        import mediapipe as mp

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        try:
            result = self.mp_landmarker.detect(mp_image)
        except Exception as e:
            logger.error(f"Error during MediaPipe pose detection: {e}")
            return {
                "detected": False,
                "model_available": True,
                "state": "Posture unavailable",
                "shoulder_tilt_deg": None,
                "shoulder_width_ratio": None,
                "posture_score": None,
                "landmarks": None
            }

        if not result.pose_landmarks or len(result.pose_landmarks) == 0:
            return {
                "detected": False,
                "model_available": True,
                "state": "Posture unavailable",
                "shoulder_tilt_deg": None,
                "shoulder_width_ratio": None,
                "posture_score": None,
                "landmarks": None
            }

        pose = result.pose_landmarks[0]

        # Landmark 11: left shoulder, Landmark 12: right shoulder
        # Landmark 0: nose
        left_shoulder = pose[11]
        right_shoulder = pose[12]
        nose = pose[0]

        # Check visibility / presence confidence
        left_vis = getattr(left_shoulder, 'visibility', 1.0)
        right_vis = getattr(right_shoulder, 'visibility', 1.0)

        # If shoulders are not visible in the frame (e.g. tightly cropped face-only shot)
        if (left_vis is not None and left_vis < 0.45) or (right_vis is not None and right_vis < 0.45) or \
           left_shoulder.y > 1.0 or right_shoulder.y > 1.0 or left_shoulder.x < 0.0 or right_shoulder.x > 1.0:
            return {
                "detected": False,
                "model_available": True,
                "state": "Posture unavailable",
                "shoulder_tilt_deg": None,
                "shoulder_width_ratio": None,
                "posture_score": None,
                "landmarks": None
            }

        # Calculate genuine shoulder tilt angle
        # In normalized coordinates: left shoulder is user's left (viewer's right or vice versa)
        dx = right_shoulder.x - left_shoulder.x
        dy = right_shoulder.y - left_shoulder.y

        # Tilt angle in degrees relative to horizontal
        tilt_deg = round(math.atan2(dy, dx) * 180.0 / math.pi, 1)
        abs_tilt = abs(tilt_deg)

        shoulder_width = math.hypot(dx, dy)
        shoulder_width_ratio = round(shoulder_width, 3)

        # Slouch detection: nose distance to shoulder midpoint vertically
        mid_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2.0
        neck_head_span = mid_shoulder_y - nose.y
        slouch_detected = bool(neck_head_span < 0.12)  # head sunk into shoulders

        # Determine posture state
        if abs_tilt > 7.0:
            state = "Shoulder tilt detected"
        elif slouch_detected:
            state = "Slouching detected"
        else:
            state = "Upright"

        # Posture score (0 - 100)
        # Optimal: tilt < 3 deg (100 pts), down to 0 at 15 deg tilt
        tilt_penalty = min(60.0, (abs_tilt / 12.0) * 60.0)
        slouch_penalty = 30.0 if slouch_detected else 0.0
        posture_score = round(max(0.0, 100.0 - tilt_penalty - slouch_penalty), 1)

        return {
            "detected": True,
            "model_available": True,
            "state": state,
            "shoulder_tilt_deg": tilt_deg,
            "shoulder_width_ratio": shoulder_width_ratio,
            "posture_score": posture_score,
            "slouch_detected": slouch_detected,
            "landmarks": {
                "left_shoulder": {
                    "x": round(left_shoulder.x, 3),
                    "y": round(left_shoulder.y, 3),
                    "pixel_x": int(left_shoulder.x * width),
                    "pixel_y": int(left_shoulder.y * height)
                },
                "right_shoulder": {
                    "x": round(right_shoulder.x, 3),
                    "y": round(right_shoulder.y, 3),
                    "pixel_x": int(right_shoulder.x * width),
                    "pixel_y": int(right_shoulder.y * height)
                },
                "nose": {
                    "x": round(nose.x, 3),
                    "y": round(nose.y, 3)
                }
            }
        }
