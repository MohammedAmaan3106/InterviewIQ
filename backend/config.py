"""
InterviewIQ Configuration Module.
Authoritative constants, file paths, model configurations, and assessment thresholds.
"""
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
MODELS_DIR = BACKEND_DIR / "models"
STATIC_DIR = FRONTEND_DIR / "static"

# Model File Paths
HAAR_FACE_PATH = MODELS_DIR / "haarcascade_frontalface_default.xml"
HAAR_EYE_PATH = MODELS_DIR / "haarcascade_eye.xml"
FACE_LANDMARKER_PATH = MODELS_DIR / "face_landmarker.task"
POSE_LANDMARKER_PATH = MODELS_DIR / "pose_landmarker_lite.task"

# Interview Execution Constants
INTERVIEW_DURATION_SECONDS = 60
TIMER_TICK_INTERVAL_SECONDS = 0.5
MIN_QUESTION_SPEAKING_SECONDS = 4.0
FINAL_QUESTION_THRESHOLD_SECONDS = 15.0

# Computer Vision Configuration
TARGET_FRAME_WIDTH = 640
TARGET_FRAME_HEIGHT = 480
FRAME_THROTTLE_FPS = 4  # Frames processed per second

# Vision Quality & Framing Thresholds
MIN_LUMINANCE = 45.0          # Below this is considered low lighting
MAX_LUMINANCE = 220.0         # Above this is considered overexposed
OPTIMAL_LUMINANCE_MIN = 70.0
OPTIMAL_LUMINANCE_MAX = 195.0

MIN_SHARPNESS_LAPLACIAN = 35.0  # Below this is considered blurry
OPTIMAL_SHARPNESS = 80.0

MIN_FACE_AREA_RATIO = 0.05    # Face bounding box area / frame area
MAX_FACE_AREA_RATIO = 0.60
OPTIMAL_FACE_AREA_MIN = 0.12
OPTIMAL_FACE_AREA_MAX = 0.45

MAX_HEAD_ROLL_TILT_DEG = 12.0 # Excessive head tilt threshold
MAX_SHOULDER_TILT_DEG = 7.0   # Excessive shoulder tilt threshold

# Speech Evaluation Configuration
OPTIMAL_WPM_MIN = 120.0
OPTIMAL_WPM_MAX = 160.0
ACCEPTABLE_WPM_MIN = 95.0
ACCEPTABLE_WPM_MAX = 185.0

FILLER_WORDS = [
    "um", "uh", "er", "ah",
    "like", "you know",
    "actually", "basically",
    "i mean", "so yeah",
    "sort of", "kind of"
]

# Scoring Weights
SCORING_WEIGHTS = {
    "answer_quality": 0.35,
    "verbal_delivery": 0.25,
    "camera_engagement": 0.20,
    "posture_presence": 0.20,
}
