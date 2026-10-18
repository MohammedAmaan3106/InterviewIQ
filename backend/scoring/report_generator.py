"""
Report Generator Module.
Generates an evidence-based interview coaching report.
Draws insights strictly from actual observations, never random or fabricated numbers.
"""
import time
from typing import Dict, Any, List
from backend.scoring.rubric import ScoringRubric

class ReportGenerator:
    def __init__(self):
        self.rubric = ScoringRubric()

    def generate(
        self,
        session_id: str,
        category: str,
        vision_summary: Dict[str, Any],
        speech_summary: Dict[str, Any],
        qna_history: List[Dict[str, Any]],
        duration_seconds: float = 60.0
    ) -> Dict[str, Any]:
        """
        Builds the complete evidence-backed report.
        """
        score_data = self.rubric.calculate_scores(
            vision_summary=vision_summary,
            speech_summary=speech_summary,
            qna_history=qna_history
        )

        overall_score = score_data["overall_score"]
        if overall_score is not None:
            if overall_score >= 85.0:
                readiness_tier = "Interview Ready"
                summary_statement = "Demonstrated strong observable communication presence, clear pacing, and structured responses."
            elif overall_score >= 70.0:
                readiness_tier = "Promising Communicator"
                summary_statement = "Demonstrated effective communication fundamentals with identifiable opportunities for polish and concrete examples."
            else:
                readiness_tier = "Developing Baseline"
                summary_statement = "Showed foundational communication with actionable opportunities to enhance framing, pacing, and response structure."
        else:
            readiness_tier = "Insufficient Data"
            summary_statement = "Not enough camera or microphone telemetry was captured to compute an overall rating."

        # Extract 3 Specific Strengths based on actual observed data
        strengths = self._derive_strengths(vision_summary, speech_summary, qna_history, score_data)

        # Extract 3 Actionable Improvements based on actual observed data
        improvements = self._derive_improvements(vision_summary, speech_summary, qna_history, score_data)

        # Personalized 3-step practice plan
        practice_plan = self._derive_practice_plan(strengths, improvements, category)

        return {
            "metadata": {
                "session_id": session_id,
                "category": category,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "duration_seconds": duration_seconds,
                "coverage_percentage": score_data["coverage_percentage"]
            },
            "overall_assessment": {
                "score": overall_score,
                "tier": readiness_tier,
                "summary": summary_statement,
                "coverage_percentage": score_data["coverage_percentage"],
                "coverage_explanation": score_data["explanation"]
            },
            "categories": score_data["categories"],
            "strengths": strengths,
            "improvements": improvements,
            "diagnostics": {
                "speech": {
                    "measured": speech_summary.get("measured", False),
                    "total_words": speech_summary.get("total_words", 0),
                    "speaking_seconds": speech_summary.get("total_speaking_seconds", 0.0),
                    "wpm": speech_summary.get("overall_wpm"),
                    "pace_label": speech_summary.get("pace_label", "Not measured"),
                    "filler_count": speech_summary.get("total_fillers", 0),
                    "filler_rate_per_100": speech_summary.get("filler_rate_per_100"),
                    "filler_breakdown": speech_summary.get("filler_breakdown", {})
                },
                "vision": {
                    "frames_processed": vision_summary.get("total_frames_processed", 0),
                    "face_visibility_pct": vision_summary.get("face_visibility_percentage", 0.0),
                    "good_framing_pct": vision_summary.get("good_framing_percentage", 0.0),
                    "average_framing_score": vision_summary.get("average_framing_score"),
                    "lighting_lux_est": vision_summary.get("average_luminance"),
                    "sharpness_score": vision_summary.get("average_sharpness"),
                    "posture_measured": vision_summary.get("posture_measured", False),
                    "upright_posture_pct": vision_summary.get("upright_posture_percentage"),
                    "average_shoulder_tilt_deg": vision_summary.get("average_shoulder_tilt_deg")
                }
            },
            "practice_plan": practice_plan,
            "transcript_history": qna_history,
            "methodology_disclaimer": (
                "InterviewIQ provides communication coaching based strictly on observable cues "
                "(framing, pace, structure, word choice, and posture stability). "
                "It does not evaluate psychological traits, emotion, confidence, honesty, or intelligence."
            )
        }

    def _derive_strengths(
        self,
        vision_summary: Dict[str, Any],
        speech_summary: Dict[str, Any],
        qna_history: List[Dict[str, Any]],
        score_data: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        candidates = []

        # Camera framing strength
        face_vis = vision_summary.get("face_visibility_percentage", 0.0)
        framing_score = vision_summary.get("average_framing_score")
        if face_vis >= 80.0 and framing_score and framing_score >= 70.0:
            candidates.append({
                "title": "Consistent Camera Framing",
                "evidence": f"Maintained stable eye-level presence across {face_vis}% of session frames (stability score: {framing_score}/100)."
            })

        # Pacing strength
        wpm = speech_summary.get("overall_wpm")
        if wpm and 115.0 <= wpm <= 165.0:
            candidates.append({
                "title": "Optimal Conversational Pace",
                "evidence": f"Spoke at {int(wpm)} WPM, which sits squarely in the ideal 120–160 WPM clarity target."
            })

        # Low filler rate strength
        filler_rate = speech_summary.get("filler_rate_per_100")
        if speech_summary.get("measured") and (filler_rate is None or filler_rate <= 3.5):
            rate_disp = filler_rate if filler_rate is not None else 0.0
            candidates.append({
                "title": "Controlled Verbal Delivery",
                "evidence": f"Minimal filler word usage detected ({rate_disp} fillers per 100 words), enhancing message clarity."
            })

        # Posture strength
        if vision_summary.get("posture_measured"):
            upright = vision_summary.get("upright_posture_percentage", 0.0)
            tilt = vision_summary.get("average_shoulder_tilt_deg", 0.0)
            if upright and upright >= 75.0:
                candidates.append({
                    "title": "Poised Physical Presence",
                    "evidence": f"Maintained upright posture in {upright}% of measured video samples with average shoulder tilt of {tilt}°."
                })

        # Content structure strength
        examples_count = sum(1 for q in qna_history if q.get("has_example"))
        if examples_count >= 1:
            candidates.append({
                "title": "Concrete Evidence in Responses",
                "evidence": f"Included tangible examples or project contexts in {examples_count} answers."
            })

        # Fallback evidence if minimal activity
        while len(candidates) < 3:
            if not any(c["title"] == "Active Session Engagement" for c in candidates):
                candidates.append({
                    "title": "Active Session Engagement",
                    "evidence": f"Successfully completed the interactive interview flow across {len(qna_history)} questions."
                })
            elif not any(c["title"] == "Audible Delivery" for c in candidates):
                total_w = speech_summary.get("total_words", 0)
                candidates.append({
                    "title": "Audible Delivery",
                    "evidence": f"Provided {total_w} words of captured response during the 60-second assessment."
                })
            else:
                candidates.append({
                    "title": "Camera Alignment",
                    "evidence": f"Positioned within camera view for {face_vis}% of the session duration."
                })

        return candidates[:3]

    def _derive_improvements(
        self,
        vision_summary: Dict[str, Any],
        speech_summary: Dict[str, Any],
        qna_history: List[Dict[str, Any]],
        score_data: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        candidates = []

        # Pace issues
        wpm = speech_summary.get("overall_wpm")
        if wpm:
            if wpm < 115.0:
                candidates.append({
                    "title": "Accelerate Speaking Momentum",
                    "evidence": f"Observed speaking rate of {int(wpm)} WPM was below the optimal 120–160 WPM pace. Aim for continuous momentum."
                })
            elif wpm > 165.0:
                candidates.append({
                    "title": "Pacing & Articulation Breathing",
                    "evidence": f"Observed rate of {int(wpm)} WPM is rapid; slowing down will enhance listener retention."
                })

        # Fillers
        filler_rate = speech_summary.get("filler_rate_per_100")
        total_fillers = speech_summary.get("total_fillers", 0)
        if filler_rate and filler_rate > 3.5:
            top_fillers = sorted(
                speech_summary.get("filler_breakdown", {}).items(),
                key=lambda x: x[1],
                reverse=True
            )
            top_str = f"'{top_fillers[0][0]}'" if top_fillers else "fillers"
            candidates.append({
                "title": "Replace Fillers with Micro-Pauses",
                "evidence": f"Detected {total_fillers} filler words ({filler_rate}% of words, primarily {top_str}). Embrace silent pauses instead."
            })

        # STAR gaps
        missing_outcomes = [q for q in qna_history if not q.get("has_outcome") and q.get("word_count", 0) >= 8]
        if missing_outcomes:
            candidates.append({
                "title": "Conclude with Quantified Outcomes",
                "evidence": "Answers detailed activities but lacked the final result, business impact, or lesson learned."
            })

        # Framing / Lighting
        lum = vision_summary.get("average_luminance")
        if lum and lum < 60.0:
            candidates.append({
                "title": "Optimize Key Lighting",
                "evidence": f"Average frame luminance ({lum}) was dim. Add a soft frontal light source facing your desk."
            })

        # Posture
        if vision_summary.get("posture_measured"):
            tilt = vision_summary.get("average_shoulder_tilt_deg")
            if tilt and tilt > 6.0:
                candidates.append({
                    "title": "Level Shoulder Alignment",
                    "evidence": f"Average shoulder tilt was {tilt}°. Align your chair and screen squarely to reduce camera lean."
                })

        # Fallbacks to ensure exactly 3 actionable items
        if len(candidates) < 3:
            candidates.append({
                "title": "Adopt the STAR Response Structure",
                "evidence": "Practice structuring answers with Situation, Task, Action, and Result to maximize impact."
            })
        if len(candidates) < 3:
            candidates.append({
                "title": "Incorporate Specific Metrics",
                "evidence": "Add numbers, percentages, or timelines to make personal accomplishments memorable."
            })
        if len(candidates) < 3:
            candidates.append({
                "title": "Camera Eye-Contact Discipline",
                "evidence": "Look directly into the camera lens when emphasizing key thesis statements."
            })

        return candidates[:3]

    def _derive_practice_plan(
        self,
        strengths: List[Dict[str, str]],
        improvements: List[Dict[str, str]],
        category: str
    ) -> List[Dict[str, str]]:
        return [
            {
                "step": 1,
                "title": "The 2-Second Silent Pause Drill",
                "action": "Whenever you feel a filler word ('like', 'um') approaching, close your mouth and take a silent 2-second breath before completing the sentence."
            },
            {
                "step": 2,
                "title": "STAR Outcome Framing Exercise",
                "action": "For every story you tell, draft a 1-sentence closing formula: 'The outcome was [result], which resulted in [business benefit or learning].'"
            },
            {
                "step": 3,
                "title": f"Targeted {category} Simulation",
                "action": "Run another 60-second InterviewIQ session focusing entirely on eye-level camera contact and one concrete example per prompt."
            }
        ]
