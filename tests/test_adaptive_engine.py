"""
Unit tests for adaptive question selection logic.
"""
from backend.interview.adaptive_engine import AdaptiveEngine

def test_initial_question():
    engine = AdaptiveEngine(category="General")
    q = engine.get_current_question()
    assert "Tell me about yourself" in q["text"]

def test_brief_answer_triggers_concrete_example_probe():
    engine = AdaptiveEngine(category="General")
    current_q = engine.get_current_question()

    # User gave a very short 6-word answer without an example
    brief_answer = "I am a reliable team worker."
    next_q = engine.decide_next_question(
        current_question_text=current_q["text"],
        transcript=brief_answer,
        speaking_duration_seconds=5.0,
        time_remaining_seconds=45.0
    )

    assert next_q["type"] == "probe_example"
    assert "concrete" in next_q["text"].lower() or "example" in next_q["text"].lower()

def test_low_time_triggers_wrap_up_question():
    engine = AdaptiveEngine(category="HR")
    current_q = engine.get_current_question()

    # When remaining time is 12 seconds, wrap up gracefully
    next_q = engine.decide_next_question(
        current_question_text=current_q["text"],
        transcript="I handled that disagreement by talking it through with my manager.",
        speaking_duration_seconds=10.0,
        time_remaining_seconds=12.0
    )

    assert next_q["type"] == "final_wrap_up"
    assert "key takeaway" in next_q["text"].lower()

def test_substantive_answer_advances_to_next_question():
    engine = AdaptiveEngine(category="Technical Fundamentals")
    current_q = engine.get_current_question()

    thorough_answer = (
        "I have five years of experience in backend systems. For example, in my previous role "
        "at Acmo I built high throughput microservices using Python and distributed queues. "
        "I love solving complex scalability challenges and collaborating with cross functional engineers."
    )
    next_q = engine.decide_next_question(
        current_question_text=current_q["text"],
        transcript=thorough_answer,
        speaking_duration_seconds=15.0,
        time_remaining_seconds=40.0
    )

    # Should advance to question 2 in the bank
    assert next_q["type"] == "skill"
    assert "skill" in next_q["text"].lower() or "proficient" in next_q["text"].lower()
