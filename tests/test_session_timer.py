"""
Unit tests for the authoritative 60-second session timer and lifecycle.
"""
import time
from backend.interview.session_manager import InterviewSessionManager

def test_session_lifecycle():
    manager = InterviewSessionManager(category="General")
    assert manager.state == "IDLE"
    assert manager.get_time_remaining() == 0.0

    start_data = manager.start()
    assert manager.state == "IN_PROGRESS"
    assert start_data["duration_seconds"] == 60
    assert 59.0 <= manager.get_time_remaining() <= 60.0
    assert not manager.is_expired()
    assert manager.current_question is not None
    assert "Tell me about yourself" in manager.current_question["text"]

def test_timer_countdown_monotonic():
    manager = InterviewSessionManager(category="Technical Fundamentals")
    manager.start()
    t1 = manager.get_time_remaining()
    time.sleep(0.1)
    t2 = manager.get_time_remaining()
    assert t2 <= t1
    assert t2 > 58.0

def test_session_completion():
    manager = InterviewSessionManager(category="Communication")
    manager.start()
    manager.update_transcript("I approach communication by actively listening to all stakeholders.")
    time.sleep(0.1)
    result = manager.complete()

    assert manager.state == "COMPLETED"
    assert result["category"] == "Communication"
    assert len(result["qna_history"]) == 1
    assert "actively listening" in result["qna_history"][0]["transcript"]
