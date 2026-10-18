"""
Unit tests for speech evaluation, pace, fillers, and relevance heuristics.
"""
from backend.speech.speech_evaluator import SpeechEvaluator
from backend.speech.answer_relevance import AnswerRelevanceEvaluator

def test_wpm_calculation():
    evaluator = SpeechEvaluator()
    # 30 words in 12 seconds = (30 / 12) * 60 = 150 WPM
    text = "This is a test of the speaking pace calculation where thirty words are spoken clearly in a twelve second interval to verify the mathematical formula is completely correct and exact."
    metrics = evaluator.analyze_text(text, duration_seconds=12.0)

    assert metrics["word_count"] >= 28
    assert metrics["wpm"] is not None
    assert 130.0 <= metrics["wpm"] <= 165.0
    assert "Optimal" in metrics["pace_label"]

def test_filler_words_counting():
    evaluator = SpeechEvaluator()
    text = "Um, I think, like, we should basically, you know, optimize the database queries."
    metrics = evaluator.analyze_text(text, duration_seconds=8.0)

    assert metrics["total_fillers"] == 4
    assert metrics["filler_counts"]["um"] == 1
    assert metrics["filler_counts"]["like"] == 1
    assert metrics["filler_counts"]["basically"] == 1
    assert metrics["filler_counts"]["you know"] == 1

def test_answer_relevance_detects_example_and_action():
    relevance_eval = AnswerRelevanceEvaluator()
    question = "Describe a difficult challenge you solved recently."
    transcript = (
        "When our payment system faced high latency during a holiday surge, "
        "I investigated the bottle necks and decided to implement Redis caching. "
        "As a result, we reduced latency by sixty percent and prevented outages."
    )

    result = relevance_eval.evaluate(question, transcript, category="Technical Fundamentals")
    assert result["measured"] is True
    assert result["score"] >= 70.0
    assert result["has_action"] is True
    assert result["has_outcome"] is True
