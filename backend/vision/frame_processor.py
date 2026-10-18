"""
Frame Processor Module.
Receives, decodes, and analyzes live webcam frames using OpenCV.
Computes frame-level quality, face metrics, and posture metrics,
and maintains aggregated metrics across the 60-second session.
"""
import base64
import time
import logging
from typing import Dict, Any, Optional
import cv2
import numpy as np

from backend.config import (
    FACE_LANDMARKER_PATH,
    POSE_LANDMARKER_PATH,
    HAAR_FACE_PATH,
    MIN_LUMINANCE,
    MAX_LUMINANCE,
    OPTIMAL_LUMINANCE_MIN,
    OPTIMAL_LUMINANCE_MAX,
    MIN_SHARPNESS_LAPLACIAN,
    FRAME_THROTTLE_FPS
)
from backend.vision.face_analyzer import FaceAnalyzer
from backend.vision.posture_analyzer import PostureAnalyzer

logger = logging.getLogger(__name__)

class FrameProcessor:
    def __init__(self):
        self.face_analyzer = FaceAnalyzer(
            mediapipe_task_path=FACE_LANDMARKER_PATH,
            haar_path=HAAR_FACE_PATH
        )
        self.posture_analyzer = PostureAnalyzer(
            mediapipe_task_path=POSE_LANDMARKER_PATH
        )
        self.last_processed_timestamp = 0.0
        self.min_frame_interval = 1.0 / FRAME_THROTTLE_FPS

        # Session-wide accumulators
        self.reset_session_metrics()

    def reset_session_metrics(self):
        """Resets all metrics for a fresh 60-second interview session."""
        self.session_metrics = {
            "total_frames_received": 0,
            "total_frames_processed": 0,
            "frames_face_detected": 0,
            "frames_good_framing": 0,
            "frames_good_lighting": 0,
            "frames_sharp": 0,
            "frames_posture_measured": 0,
            "frames_upright_posture": 0,
            "luminance_samples": [],
            "sharpness_samples": [],
            "framing_score_samples": [],
            "posture_score_samples": [],
            "shoulder_tilt_samples": [],
            "head_roll_samples": []
        }

    def process_base64_frame(self, base64_data: str, force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Decodes a base64 encoded JPEG/PNG frame and executes OpenCV vision analysis.
        Throttles processing to FRAME_THROTTLE_FPS to keep countdown and event loop responsive.
        """
        now = time.monotonic()
        self.session_metrics["total_frames_received"] += 1

        if not force and (now - self.last_processed_timestamp) < self.min_frame_interval:
            # Throttled to maintain responsiveness
            return None

        self.last_processed_timestamp = now

        # Strip data URL prefix if present
        if "," in base64_data:
            _, base64_data = base64_data.split(",", 1)

        try:
            image_bytes = base64.b64decode(base64_data)
            np_arr = np.frombuffer(image_bytes, np.uint8)
            frame_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.warning(f"Error decoding image frame: {e}")
            return None

        if frame_bgr is None or frame_bgr.size == 0:
            return None

        return self.process_cv_frame(frame_bgr)

    def process_cv_frame(self, frame_bgr: np.ndarray) -> Dict[str, Any]:
        """
        Executes real OpenCV and MediaPipe analysis on a decoded BGR image.
        """
        self.session_metrics["total_frames_processed"] += 1
        height, width = frame_bgr.shape[:2]

        # 1. Real Frame Quality Checks (Luminance & Sharpness)
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        luminance = float(np.mean(gray))
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        # Lighting classification
        if luminance < MIN_LUMINANCE:
            lighting_state = "Low lighting"
        elif luminance > MAX_LUMINANCE:
            lighting_state = "Overexposed"
        else:
            lighting_state = "Good lighting"

        # Sharpness classification
        sharpness_state = "Sharp" if sharpness >= MIN_SHARPNESS_LAPLACIAN else "Blurry"

        # 2. Real Face Analysis
        face_result = self.face_analyzer.analyze(frame_bgr)

        # 3. Real Posture Analysis
        posture_result = self.posture_analyzer.analyze(frame_bgr)

        # 4. Accumulate session observations
        self.session_metrics["luminance_samples"].append(luminance)
        self.session_metrics["sharpness_samples"].append(sharpness)

        if lighting_state == "Good lighting":
            self.session_metrics["frames_good_lighting"] += 1
        if sharpness_state == "Sharp":
            self.session_metrics["frames_sharp"] += 1

        if face_result.get("detected"):
            self.session_metrics["frames_face_detected"] += 1
            if face_result.get("framing_state") == "Good framing":
                self.session_metrics["frames_good_framing"] += 1
            if face_result.get("framing_score") is not None:
                self.session_metrics["framing_score_samples"].append(face_result["framing_score"])
            if face_result.get("head_pose") and face_result["head_pose"].get("roll_deg") is not None:
                self.session_metrics["head_roll_samples"].append(abs(face_result["head_pose"]["roll_deg"]))

        if posture_result.get("detected"):
            self.session_metrics["frames_posture_measured"] += 1
            if posture_result.get("state") == "Upright":
                self.session_metrics["frames_upright_posture"] += 1
            if posture_result.get("posture_score") is not None:
                self.session_metrics["posture_score_samples"].append(posture_result["posture_score"])
            if posture_result.get("shoulder_tilt_deg") is not None:
                self.session_metrics["shoulder_tilt_samples"].append(abs(posture_result["shoulder_tilt_deg"]))

        return {
            "timestamp": time.time(),
            "frame_width": width,
            "frame_height": height,
            "quality": {
                "luminance": round(luminance, 1),
                "lighting_state": lighting_state,
                "sharpness": round(sharpness, 1),
                "sharpness_state": sharpness_state
            },
            "face": face_result,
            "posture": posture_result
        }

    def get_session_summary(self) -> Dict[str, Any]:
        """
        Compiles the observed camera and posture telemetry across the entire 60s interview.
        """
        total = max(1, self.session_metrics["total_frames_processed"])
        face_detected_ratio = self.session_metrics["frames_face_detected"] / total
        good_framing_ratio = self.session_metrics["frames_good_framing"] / max(1, self.session_metrics["frames_face_detected"])

        posture_measured_count = self.session_metrics["frames_posture_measured"]
        posture_measured = bool(posture_measured_count >= 3)
        upright_ratio = (self.session_metrics["frames_upright_posture"] / max(1, posture_measured_count)) if posture_measured else None

        avg_framing_score = (
            round(float(np.mean(self.session_metrics["framing_score_samples"])), 1)
            if self.session_metrics["framing_score_samples"] else None
        )

        avg_posture_score = (
            round(float(np.mean(self.session_metrics["posture_score_samples"])), 1)
            if (posture_measured and self.session_metrics["posture_score_samples"]) else None
        )

        avg_luminance = (
            round(float(np.mean(self.session_metrics["luminance_samples"])), 1)
            if self.session_metrics["luminance_samples"] else None
        )

        avg_sharpness = (
            round(float(np.mean(self.session_metrics["sharpness_samples"])), 1)
            if self.session_metrics["sharpness_samples"] else None
        )

        avg_shoulder_tilt = (
            round(float(np.mean(self.session_metrics["shoulder_tilt_samples"])), 1)
            if (posture_measured and self.session_metrics["shoulder_tilt_samples"]) else None
        )

        return {
            "total_frames_processed": self.session_metrics["total_frames_processed"],
            "face_visibility_percentage": round(face_detected_ratio * 100.0, 1),
            "good_framing_percentage": round(good_framing_ratio * 100.0, 1) if self.session_metrics["frames_face_detected"] > 0 else 0.0,
            "average_framing_score": avg_framing_score,
            "average_luminance": avg_luminance,
            "average_sharpness": avg_sharpness,
            "posture_measured": posture_measured,
            "upright_posture_percentage": round(upright_ratio * 100.0, 1) if upright_ratio is not None else None,
            "average_posture_score": avg_posture_score,
            "average_shoulder_tilt_deg": avg_shoulder_tilt
        }
