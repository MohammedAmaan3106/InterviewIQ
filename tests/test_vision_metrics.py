"""
Unit tests for OpenCV frame processing, luminance, sharpness, and vision accumulators.
"""
import numpy as np
import cv2
from backend.vision.frame_processor import FrameProcessor

def test_frame_luminance_and_sharpness():
    processor = FrameProcessor()

    # Create a synthetic 640x480 image with moderate brightness and high-contrast lines
    img = np.full((480, 640, 3), 128, dtype=np.uint8)
    cv2.rectangle(img, (100, 100), (300, 300), (255, 255, 255), -1)
    cv2.line(img, (0, 0), (640, 480), (0, 0, 0), 5)

    result = processor.process_cv_frame(img)
    assert result is not None
    assert "quality" in result
    assert result["quality"]["lighting_state"] == "Good lighting"
    assert result["quality"]["luminance"] > 80.0
    assert result["quality"]["sharpness"] > 0.0

def test_low_lighting_detection():
    processor = FrameProcessor()

    # Very dark frame
    dark_img = np.full((480, 640, 3), 20, dtype=np.uint8)
    result = processor.process_cv_frame(dark_img)

    assert result["quality"]["lighting_state"] == "Low lighting"
    assert result["quality"]["luminance"] <= 40.0

def test_session_summary_aggregation():
    processor = FrameProcessor()
    img = np.full((480, 640, 3), 120, dtype=np.uint8)

    for _ in range(5):
        processor.process_cv_frame(img)

    summary = processor.get_session_summary()
    assert summary["total_frames_processed"] == 5
    assert summary["average_luminance"] is not None
    assert 115.0 <= summary["average_luminance"] <= 125.0
