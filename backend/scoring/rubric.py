"""
Scoring Rubric Module.
Computes 4 explainable category scores with proportional dynamic re-weighting
when metrics cannot be reliably measured. Missing data is never treated as zero.
"""
from typing import Dict, Any, List, Optional
from backend.config import SCORING_WEIGHTS

class ScoringRubric:
    def __init__(self):
        self.base_weights = dict(SCORING_WEIGHTS)

    def calculate_scores(
        self,
        vision_summary: Dict[str, Any],
        speech_summary: Dict[str, Any],
        qna_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculates category scores, applies proportional weight normalization,
        and computes data coverage.
        """
        categories = {}

        # 1. Answer Quality (Base 35%)
        valid_relevance_scores = [
            q["relevance_score"] for q in qna_history
            if q.get("relevance_score") is not None
        ]
        if valid_relevance_scores:
            aq_score = round(sum(valid_relevance_scores) / len(valid_relevance_scores), 1)
            categories["answer_quality"] = {
                "name": "Answer Quality",
                "base_weight": self.base_weights["answer_quality"],
                "measured": True,
                "score": aq_score,
                "label": "Evaluated with local STAR & example heuristics",
                "observations": [
                    f"Assessed {len(valid_relevance_scores)} responses for structure, depth, and examples.",
                    f"Average heuristic answer score: {aq_score}/100."
                ]
            }
        else:
            categories["answer_quality"] = {
                "name": "Answer Quality",
                "base_weight": self.base_weights["answer_quality"],
                "measured": False,
                "score": None,
                "label": "Not measured",
                "observations": ["No substantive spoken or written responses were provided."]
            }

        # 2. Verbal Delivery (Base 25%)
        if speech_summary.get("measured") and speech_summary.get("average_verbal_score") is not None:
            vd_score = speech_summary["average_verbal_score"]
            wpm = speech_summary.get("overall_wpm")
            fillers = speech_summary.get("total_fillers", 0)
            rate = speech_summary.get("filler_rate_per_100")
            categories["verbal_delivery"] = {
                "name": "Verbal Delivery",
                "base_weight": self.base_weights["verbal_delivery"],
                "measured": True,
                "score": vd_score,
                "label": f"{speech_summary.get('pace_label', 'Paced')} delivery",
                "observations": [
                    f"Observed speaking pace: {wpm} words/min ({speech_summary.get('pace_label', 'Active')}).",
                    f"Counted {fillers} filler words ({rate if rate is not None else 0}% of spoken words)."
                ]
            }
        else:
            categories["verbal_delivery"] = {
                "name": "Verbal Delivery",
                "base_weight": self.base_weights["verbal_delivery"],
                "measured": False,
                "score": None,
                "label": "Not measured",
                "observations": ["Speech recognition data was unavailable or speaking duration was too short."]
            }

        # 3. Camera Engagement (Base 20%)
        total_frames = vision_summary.get("total_frames_processed", 0)
        face_vis_pct = vision_summary.get("face_visibility_percentage", 0.0)
        framing_score = vision_summary.get("average_framing_score")

        if total_frames >= 4 and face_vis_pct > 0.0 and framing_score is not None:
            # Score components: visibility (40%), framing stability (40%), lighting/sharpness (20%)
            vis_pts = (face_vis_pct / 100.0) * 40.0
            frame_pts = (framing_score / 100.0) * 40.0
            lum = vision_summary.get("average_luminance") or 100.0
            quality_pts = 20.0 if (50.0 <= lum <= 200.0) else 10.0
            ce_score = round(min(100.0, vis_pts + frame_pts + quality_pts), 1)

            categories["camera_engagement"] = {
                "name": "Camera Engagement",
                "base_weight": self.base_weights["camera_engagement"],
                "measured": True,
                "score": ce_score,
                "label": "Observed via OpenCV live frame analysis",
                "observations": [
                    f"Face detected in {face_vis_pct}% of processed video frames.",
                    f"Average framing stability score: {framing_score}/100.",
                    f"Mean frame luminance: {vision_summary.get('average_luminance')}."
                ]
            }
        else:
            categories["camera_engagement"] = {
                "name": "Camera Engagement",
                "base_weight": self.base_weights["camera_engagement"],
                "measured": False,
                "score": None,
                "label": "Not measured",
                "observations": ["Camera was inaccessible, disabled, or no face was detected in frames."]
            }

        # 4. Posture and Presence (Base 20%)
        posture_measured = vision_summary.get("posture_measured", False)
        posture_score = vision_summary.get("average_posture_score")

        if posture_measured and posture_score is not None:
            upright_pct = vision_summary.get("upright_posture_percentage")
            tilt = vision_summary.get("average_shoulder_tilt_deg")
            categories["posture_presence"] = {
                "name": "Posture and Presence",
                "base_weight": self.base_weights["posture_presence"],
                "measured": True,
                "score": posture_score,
                "label": "Observed via MediaPipe body pose landmarks",
                "observations": [
                    f"Maintained upright posture in {upright_pct}% of measured frames.",
                    f"Average shoulder tilt angle: {tilt}° from horizontal."
                ]
            }
        else:
            categories["posture_presence"] = {
                "name": "Posture and Presence",
                "base_weight": self.base_weights["posture_presence"],
                "measured": False,
                "score": None,
                "label": "Not measured",
                "observations": [
                    "Shoulders or torso were outside camera frame (close-up view) or pose model unavailable."
                ]
            }

        # Proportional Weight Normalization
        measured_categories = [k for k, v in categories.items() if v["measured"]]
        measured_weight_sum = sum(categories[k]["base_weight"] for k in measured_categories)
        coverage_percentage = round((len(measured_categories) / len(categories)) * 100.0, 1)

        overall_score = None
        normalized_weights = {}

        if measured_weight_sum > 0 and len(measured_categories) >= 2:
            weighted_sum = 0.0
            accumulated_weight = 0.0
            for idx, k in enumerate(measured_categories):
                norm_w = categories[k]["base_weight"] / measured_weight_sum
                normalized_weights[k] = round(norm_w, 4)
                weighted_sum += norm_w * categories[k]["score"]
                
                # For the last measured category, ensure exact 100.0 total sum
                if idx == len(measured_categories) - 1:
                    categories[k]["effective_weight"] = round(100.0 - accumulated_weight, 1)
                else:
                    eff_w = round(norm_w * 100.0, 1)
                    categories[k]["effective_weight"] = eff_w
                    accumulated_weight += eff_w

            overall_score = round(weighted_sum, 1)
        else:
            for k in categories:
                categories[k]["effective_weight"] = round(categories[k]["base_weight"] * 100.0, 1)

        return {
            "overall_score": overall_score,
            "coverage_percentage": coverage_percentage,
            "measured_count": len(measured_categories),
            "total_categories": len(categories),
            "categories": categories,
            "explanation": (
                f"Overall score reflects {len(measured_categories)} of 4 measured categories. "
                "Unmeasured indicators were proportionally redistributed without penalizing overall rating."
                if measured_weight_sum > 0 else "Insufficient data to compute an overall score."
            )
        }
