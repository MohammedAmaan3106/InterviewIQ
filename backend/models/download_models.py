"""
Model downloader script for InterviewIQ.
Downloads official OpenCV Haar cascades and Google MediaPipe vision task models
into the local backend/models directory for offline, zero-cloud operation.
"""
import os
import urllib.request
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

MODELS_DIR = os.path.dirname(os.path.abspath(__file__))

MODELS = {
    "haarcascade_frontalface_default.xml": (
        "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml",
        "OpenCV Frontal Face Haar Cascade (fallback detector)"
    ),
    "haarcascade_eye.xml": (
        "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_eye.xml",
        "OpenCV Eye Detection Haar Cascade"
    ),
    "face_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
        "Google MediaPipe Face Landmarker (478 3D landmarks)"
    ),
    "pose_landmarker_lite.task": (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
        "Google MediaPipe Pose Landmarker Lite (33 body pose landmarks)"
    )
}

def download_models(force=False):
    os.makedirs(MODELS_DIR, exist_ok=True)
    status_results = {}
    for filename, (url, description) in MODELS.items():
        target_path = os.path.join(MODELS_DIR, filename)
        if os.path.exists(target_path) and not force and os.path.getsize(target_path) > 1000:
            logging.info(f"[EXISTS] {filename} ({description}) - {os.path.getsize(target_path)} bytes")
            status_results[filename] = True
            continue

        logging.info(f"[DOWNLOADING] {filename} from {url}...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "InterviewIQ-Downloader/1.0"})
            with urllib.request.urlopen(req, timeout=15) as response, open(target_path, "wb") as out_file:
                content = response.read()
                out_file.write(content)
            logging.info(f"[DOWNLOADED] {filename} ({len(content)} bytes)")
            status_results[filename] = True
        except Exception as e:
            logging.warning(f"[SKIPPED] Failed to download {filename}: {e}")
            status_results[filename] = False

    return status_results

if __name__ == "__main__":
    download_models()
