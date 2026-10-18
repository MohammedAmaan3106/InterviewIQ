"""
Unit tests for the scoring rubric and weight normalization.
"""
from backend.scoring.rubric import ScoringRubric

def test_four_category_scoring_when_all_measured():
    rubric = ScoringRubric()

    vision_summary = {
        "total_frames_processed": 50,
        "face_visibility_percentage": 95.0,
        "good_framing_percentage": 90.0,
        "average_framing_score": 88.0,
        "average_luminance": 120.0,
        "average_sharpness": 110.0,
        "posture_measured": True,
        "upright_posture_percentage": 85.0,
        "average_posture_score": 90.0,
        "average_shoulder_tilt_deg": 2.1
    }

    speech_summary = {
        "measured": True,
        "total_words": 65,
        "total_speaking_seconds": 28.0,
        "overall_wpm": 139.3,
        "pace_label": "Optimal pace (139 WPM)",
        "total_fillers": 1,
        "filler_rate_per_100": 1.5,
        "average_verbal_score": 92.0
    }

    qna_history = [
        {
            "relevance_score": 85.0,
            "has_example": True,
            "has_action": True,
            "has_outcome": True
        }
    ]

    result = rubric.calculate_scores(vision_summary, speech_summary, qna_history)

    assert result["coverage_percentage"] == 100.0
    assert result["measured_count"] == 4
    assert result["overall_score"] is not None
    assert 80.0 <= result["overall_score"] <= 95.0

    cats = result["categories"]
    assert cats["answer_quality"]["measured"] is True
    assert cats["verbal_delivery"]["measured"] is True
    assert cats["camera_engagement"]["measured"] is True
    assert cats["posture_presence"]["measured"] is True

    # Base weights: 35%, 25%, 20%, 20%
    assert cats["answer_quality"]["effective_weight"] == 35.0
    assert cats["verbal_delivery"]["effective_weight"] == 25.0
    assert cats["camera_engagement"]["effective_weight"] == 20.0
    assert cats["posture_presence"]["effective_weight"] == 20.0

def test_proportional_reweighting_when_posture_unmeasured():
    rubric = ScoringRubric()

    # Posture is unmeasured (e.g. webcam cropped tightly at neck/face)
    vision_summary = {
        "total_frames_processed": 50,
        "face_visibility_percentage": 95.0,
        "average_framing_score": 85.0,
        "average_luminance": 110.0,
        "posture_measured": False,
        "average_posture_score": None
    }

    speech_summary = {
        "measured": True,
        "total_words": 60,
        "overall_wpm": 130.0,
        "average_verbal_score": 90.0
    }

    qna_history = [{"relevance_score": 80.0}]

    result = rubric.calculate_scores(vision_summary, speech_summary, qna_history)

    assert result["coverage_percentage"] == 75.0
    assert result["measured_count"] == 3
    cats = result["categories"]

    assert cats["posture_presence"]["measured"] is False
    assert cats["posture_presence"]["score"] is None
    assert cats["posture_presence"]["label"] == "Not measured"

    # Remaining 3 categories had base weights 0.35, 0.25, 0.20 (total 0.80)
    # Normalized weights: 0.35/0.80 = 43.75%, 0.25/0.80 = 31.25%, 0.20/0.80 = 25.0%
    total_effective_weight = (
        cats["answer_quality"]["effective_weight"] +
        cats["verbal_delivery"]["effective_weight"] +
        cats["camera_engagement"]["effective_weight"]
    )
    assert round(total_effective_weight, 1) == 100.0
    assert result["overall_score"] is not None
    # Ensure missing posture did NOT turn into a 0 that lowered the score
    assert result["overall_score"] >= 75.0
