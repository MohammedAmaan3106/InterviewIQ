"""
Interview Session Manager Module.
Maintains the authoritative 60-second interview clock, session state machine,
question transitions, and hardware event coordination.
"""
import time
import uuid
import logging
from typing import Dict, Any, List, Optional

from backend.config import INTERVIEW_DURATION_SECONDS
from backend.interview.adaptive_engine import AdaptiveEngine
from backend.vision.frame_processor import FrameProcessor
from backend.speech.speech_evaluator import SpeechEvaluator
from backend.speech.answer_relevance import AnswerRelevanceEvaluator

logger = logging.getLogger(__name__)

class InterviewSessionManager:
    def __init__(self, category: str = "General"):
        self.session_id = str(uuid.uuid4())[:8]
        self.category = category
        self.state = "IDLE"  # IDLE, IN_PROGRESS, COMPLETED, CANCELLED

        self.start_monotonic: Optional[float] = None
        self.duration_seconds = INTERVIEW_DURATION_SECONDS

        self.frame_processor = FrameProcessor()
        self.speech_evaluator = SpeechEvaluator()
        self.relevance_evaluator = AnswerRelevanceEvaluator()
        self.adaptive_engine = AdaptiveEngine(category=category)

        self.qna_history: List[Dict[str, Any]] = []
        self.current_question: Optional[Dict[str, Any]] = None
        self.current_question_start_time: Optional[float] = None
        self.current_answer_text = ""
        self.current_answer_start_monotonic: Optional[float] = None

    def start(self) -> Dict[str, Any]:
        """Starts the authoritative 60-second interview session."""
        self.state = "IN_PROGRESS"
        self.start_monotonic = time.monotonic()
        self.frame_processor.reset_session_metrics()
        self.speech_evaluator.reset()

        initial_q = self.adaptive_engine.get_current_question()
        self.current_question = initial_q
        self.current_question_start_time = time.time()
        self.current_answer_text = ""
        self.current_answer_start_monotonic = time.monotonic()

        logger.info(f"Session {self.session_id} started. Category: {self.category}.")
        return {
            "session_id": self.session_id,
            "category": self.category,
            "duration_seconds": self.duration_seconds,
            "time_remaining_seconds": self.duration_seconds,
            "question": self.current_question
        }

    def get_time_remaining(self) -> float:
        """Calculates exact authoritative seconds remaining in the session."""
        if self.state != "IN_PROGRESS" or self.start_monotonic is None:
            return 0.0
        elapsed = time.monotonic() - self.start_monotonic
        remaining = max(0.0, self.duration_seconds - elapsed)
        return round(remaining, 1)

    def is_expired(self) -> bool:
        """True if the 60-second timer has elapsed."""
        if self.state != "IN_PROGRESS":
            return False
        return self.get_time_remaining() <= 0.0

    def update_transcript(self, text: str, is_final: bool = False):
        """Appends or updates speech transcript for current answer."""
        if self.state != "IN_PROGRESS":
            return
        self.current_answer_text = text
        self.speech_evaluator.record_speech_event(text, is_final=is_final)

    def advance_question(self, manual_transcript: Optional[str] = None) -> Dict[str, Any]:
        """
        Finalizes candidate's answer for current question, assesses it,
        and asks adaptive engine for the next question.
        """
        if self.state != "IN_PROGRESS":
            return {}

        final_transcript = manual_transcript if manual_transcript is not None else self.current_answer_text
        speaking_duration = 0.0
        if self.current_answer_start_monotonic is not None:
            speaking_duration = max(0.5, time.monotonic() - self.current_answer_start_monotonic)

        # Evaluate spoken delivery
        speech_metrics = self.speech_evaluator.analyze_text(final_transcript, speaking_duration)

        # Evaluate content relevance heuristics
        relevance_metrics = self.relevance_evaluator.evaluate(
            question=self.current_question["text"] if self.current_question else "",
            transcript=final_transcript,
            category=self.category
        )

        # Record this Q&A entry
        entry = {
            "question_id": self.current_question.get("id") if self.current_question else "",
            "question_text": self.current_question.get("text") if self.current_question else "",
            "transcript": final_transcript,
            "speaking_duration_seconds": speech_metrics["duration_seconds"],
            "word_count": speech_metrics["word_count"],
            "wpm": speech_metrics["wpm"],
            "pace_label": speech_metrics["pace_label"],
            "fillers_count": speech_metrics["total_fillers"],
            "filler_rate_per_100": speech_metrics["filler_rate_per_100"],
            "verbal_score": speech_metrics["verbal_score"],
            "relevance_score": relevance_metrics["score"],
            "relevance_label": relevance_metrics["label"],
            "has_example": relevance_metrics["has_example"],
            "has_action": relevance_metrics["has_action"],
            "has_outcome": relevance_metrics["has_outcome"],
            "evidence": relevance_metrics["evidence"],
            "missing_elements": relevance_metrics["missing_elements"],
            "timestamp": time.time()
        }
        self.qna_history.append(entry)

        # Request next question from adaptive engine
        time_rem = self.get_time_remaining()
        next_q = self.adaptive_engine.decide_next_question(
            current_question_text=entry["question_text"],
            transcript=final_transcript,
            speaking_duration_seconds=speaking_duration,
            time_remaining_seconds=time_rem
        )

        self.current_question = next_q
        self.current_question_start_time = time.time()
        self.current_answer_text = ""
        self.current_answer_start_monotonic = time.monotonic()

        return {
            "previous_answer_summary": entry,
            "next_question": next_q,
            "time_remaining_seconds": time_rem
        }

    def complete(self) -> Dict[str, Any]:
        """Finalizes the interview session and gathers raw observation telemetry."""
        # If there is an unfinished response currently being spoken, record it
        if self.state == "IN_PROGRESS" and self.current_question:
            speaking_duration = 0.0
            if self.current_answer_start_monotonic:
                speaking_duration = max(0.5, time.monotonic() - self.current_answer_start_monotonic)

            speech_metrics = self.speech_evaluator.analyze_text(self.current_answer_text, speaking_duration)
            relevance_metrics = self.relevance_evaluator.evaluate(
                question=self.current_question["text"],
                transcript=self.current_answer_text,
                category=self.category
            )
            self.qna_history.append({
                "question_id": self.current_question.get("id", ""),
                "question_text": self.current_question.get("text", ""),
                "transcript": self.current_answer_text,
                "speaking_duration_seconds": speech_metrics["duration_seconds"],
                "word_count": speech_metrics["word_count"],
                "wpm": speech_metrics["wpm"],
                "pace_label": speech_metrics["pace_label"],
                "fillers_count": speech_metrics["total_fillers"],
                "filler_rate_per_100": speech_metrics["filler_rate_per_100"],
                "verbal_score": speech_metrics["verbal_score"],
                "relevance_score": relevance_metrics["score"],
                "relevance_label": relevance_metrics["label"],
                "has_example": relevance_metrics["has_example"],
                "has_action": relevance_metrics["has_action"],
                "has_outcome": relevance_metrics["has_outcome"],
                "evidence": relevance_metrics["evidence"],
                "missing_elements": relevance_metrics["missing_elements"],
                "timestamp": time.time()
            })

        self.state = "COMPLETED"
        vision_summary = self.frame_processor.get_session_summary()
        speech_summary = self.speech_evaluator.summarize_session(self.qna_history)

        return {
            "session_id": self.session_id,
            "category": self.category,
            "duration_seconds": self.duration_seconds,
            "vision_summary": vision_summary,
            "speech_summary": speech_summary,
            "qna_history": self.qna_history
        }
