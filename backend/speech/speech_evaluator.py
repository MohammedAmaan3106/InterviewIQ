"""
Speech Evaluator Module.
Evaluates spoken candidate answers for speaking pace (WPM),
filler words count, measured speaking duration, and pauses.
"""
import re
import time
import logging
from typing import Dict, Any, List, Optional
from backend.config import (
    OPTIMAL_WPM_MIN,
    OPTIMAL_WPM_MAX,
    ACCEPTABLE_WPM_MIN,
    ACCEPTABLE_WPM_MAX,
    FILLER_WORDS
)

logger = logging.getLogger(__name__)

class SpeechEvaluator:
    def __init__(self):
        # Build regex patterns for filler words with word boundaries
        self.filler_patterns = {}
        for fw in FILLER_WORDS:
            # Handle multi-word fillers like 'you know', 'so yeah', 'i mean'
            escaped = re.escape(fw).replace(r"\ ", r"\s+")
            self.filler_patterns[fw] = re.compile(rf"\b{escaped}\b", re.IGNORECASE)

        self.reset()

    def reset(self):
        """Resets all metrics for a fresh interview session."""
        self.answers: List[Dict[str, Any]] = []
        self.current_utterance_start: Optional[float] = None
        self.last_speech_time: Optional[float] = None
        self.pauses: List[float] = []

    def record_speech_event(self, text: str, is_final: bool = False):
        """Records speech activity timestamp to track real pauses."""
        now = time.monotonic()
        if self.current_utterance_start is None:
            self.current_utterance_start = now

        if self.last_speech_time is not None:
            gap = now - self.last_speech_time
            if gap >= 2.5:  # Pause threshold
                self.pauses.append(round(gap, 1))

        self.last_speech_time = now

    def analyze_text(self, transcript: str, duration_seconds: float) -> Dict[str, Any]:
        """
        Analyzes a single answer's transcript and speaking duration.
        """
        cleaned_text = transcript.strip()
        words = re.findall(r"\b[a-zA-Z0-9']+\b", cleaned_text)
        word_count = len(words)

        # Filler words analysis
        filler_counts: Dict[str, int] = {}
        total_fillers = 0

        for filler, pattern in self.filler_patterns.items():
            matches = len(pattern.findall(cleaned_text))
            if matches > 0:
                filler_counts[filler] = matches
                total_fillers += matches

        # Speaking pace (WPM)
        wpm = None
        pace_label = "Not measured"

        # Reliable pace measurement requires at least 5 words and 3 seconds of speaking
        if word_count >= 5 and duration_seconds >= 3.0:
            wpm = round((word_count / duration_seconds) * 60.0, 1)
            if OPTIMAL_WPM_MIN <= wpm <= OPTIMAL_WPM_MAX:
                pace_label = f"Optimal pace ({int(wpm)} WPM)"
            elif wpm < OPTIMAL_WPM_MIN:
                pace_label = f"Deliberate/Slow pace ({int(wpm)} WPM)"
            else:
                pace_label = f"Rapid pace ({int(wpm)} WPM)"

        # Fillers per 100 words
        filler_rate_per_100 = None
        if word_count >= 10:
            filler_rate_per_100 = round((total_fillers / word_count) * 100.0, 1)

        # Verbal delivery score (0 - 100)
        verbal_score = None
        if wpm is not None:
            # Score on pace (50 pts)
            if OPTIMAL_WPM_MIN <= wpm <= OPTIMAL_WPM_MAX:
                pace_pts = 50.0
            elif ACCEPTABLE_WPM_MIN <= wpm <= ACCEPTABLE_WPM_MAX:
                pace_pts = 38.0
            else:
                pace_pts = max(15.0, 50.0 - abs(wpm - 140.0) * 0.5)

            # Score on fillers (50 pts)
            rate = filler_rate_per_100 if filler_rate_per_100 is not None else 0.0
            if rate <= 2.0:
                filler_pts = 50.0
            elif rate <= 5.0:
                filler_pts = 40.0
            elif rate <= 8.0:
                filler_pts = 28.0
            else:
                filler_pts = max(10.0, 50.0 - (rate - 8.0) * 4.0)

            verbal_score = round(pace_pts + filler_pts, 1)

        return {
            "word_count": word_count,
            "duration_seconds": round(duration_seconds, 1),
            "wpm": wpm,
            "pace_label": pace_label,
            "total_fillers": total_fillers,
            "filler_counts": filler_counts,
            "filler_rate_per_100": filler_rate_per_100,
            "verbal_score": verbal_score,
            "pauses_count": len(self.pauses)
        }

    def summarize_session(self, all_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregates verbal delivery metrics across all interview questions.
        """
        total_words = sum(a.get("word_count", 0) for a in all_answers)
        total_duration = sum(a.get("duration_seconds", 0.0) for a in all_answers)
        total_fillers = sum(a.get("total_fillers", 0) for a in all_answers)

        combined_filler_counts: Dict[str, int] = {}
        for a in all_answers:
            for f, cnt in a.get("filler_counts", {}).items():
                combined_filler_counts[f] = combined_filler_counts.get(f, 0) + cnt

        measured = bool(total_words >= 8 and total_duration >= 4.0)

        overall_wpm = None
        pace_label = "Not measured"
        if measured:
            overall_wpm = round((total_words / total_duration) * 60.0, 1)
            if OPTIMAL_WPM_MIN <= overall_wpm <= OPTIMAL_WPM_MAX:
                pace_label = f"Optimal pace ({int(overall_wpm)} WPM)"
            elif overall_wpm < OPTIMAL_WPM_MIN:
                pace_label = f"Deliberate/Slow pace ({int(overall_wpm)} WPM)"
            else:
                pace_label = f"Rapid pace ({int(overall_wpm)} WPM)"

        filler_rate = round((total_fillers / total_words) * 100.0, 1) if (measured and total_words > 0) else None

        # Average verbal score across valid answers
        valid_scores = [a["verbal_score"] for a in all_answers if a.get("verbal_score") is not None]
        avg_score = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else None

        return {
            "measured": measured,
            "total_words": total_words,
            "total_speaking_seconds": round(total_duration, 1),
            "overall_wpm": overall_wpm,
            "pace_label": pace_label,
            "total_fillers": total_fillers,
            "filler_breakdown": combined_filler_counts,
            "filler_rate_per_100": filler_rate,
            "average_verbal_score": avg_score,
            "total_pauses_recorded": len(self.pauses)
        }
