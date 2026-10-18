"""
End-to-End WebSocket and API integration tests for InterviewIQ.
Tests client connection, session initialization, real frame transmission,
authoritative timer ticks, question advance, and report generation.
"""
import json
import base64
import numpy as np
import cv2
from starlette.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_http_endpoints():
    # Health Check
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    data = res_health.json()
    assert data["status"] == "healthy"
    assert data["models"]["haar_cascade_face"] is True

    # Categories
    res_cats = client.get("/api/categories")
    assert res_cats.status_code == 200
    cats = res_cats.json()["categories"]
    assert "General" in cats
    assert "Technical Fundamentals" in cats

    # Root HTML
    res_index = client.get("/")
    assert res_index.status_code == 200
    assert "InterviewIQ" in res_index.text

def test_websocket_interview_flow():
    with client.websocket_connect("/ws/interview") as ws:
        # 1. Start Interview Session
        ws.send_text(json.dumps({
            "type": "start_session",
            "category": "General"
        }))

        msg_started = json.loads(ws.receive_text())
        assert msg_started["type"] == "session_started"
        assert msg_started["data"]["category"] == "General"
        assert "Tell me about yourself" in msg_started["data"]["question"]["text"]

        # 2. Send Real Webcam Frame (Base64 JPEG)
        img = np.full((480, 640, 3), 128, dtype=np.uint8)
        cv2.rectangle(img, (200, 150), (440, 390), (200, 200, 200), -1)
        _, buffer = cv2.imencode('.jpg', img)
        b64_frame = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

        ws.send_text(json.dumps({
            "type": "video_frame",
            "frame": b64_frame
        }))

        # Wait for vision telemetry or timer tick
        received_types = []
        for _ in range(3):
            msg = json.loads(ws.receive_text())
            received_types.append(msg["type"])
            if msg["type"] == "vision_telemetry":
                assert "quality" in msg["data"]
                assert msg["data"]["quality"]["lighting_state"] == "Good lighting"

        assert any(t in ["vision_telemetry", "timer_tick"] for t in received_types)

        # 3. Send Transcript
        ws.send_text(json.dumps({
            "type": "transcript_update",
            "text": "I am a passionate software engineer with five years of experience.",
            "is_final": True
        }))

        # 4. Advance Question
        ws.send_text(json.dumps({
            "type": "advance_question"
        }))

        msg_next = json.loads(ws.receive_text())
        while msg_next["type"] == "timer_tick":
            msg_next = json.loads(ws.receive_text())

        assert msg_next["type"] == "question_advanced"
        assert "next_question" in msg_next["data"]

        # 5. Stop Session Early and Receive Complete Report
        ws.send_text(json.dumps({
            "type": "stop_session"
        }))

        msg_report = json.loads(ws.receive_text())
        while msg_report["type"] == "timer_tick":
            msg_report = json.loads(ws.receive_text())

        assert msg_report["type"] == "session_completed"
        report = msg_report["report"]
        assert "overall_assessment" in report
        assert "categories" in report
        assert "strengths" in report
        assert len(report["strengths"]) == 3
        assert "improvements" in report
        assert len(report["improvements"]) == 3
        assert "practice_plan" in report
