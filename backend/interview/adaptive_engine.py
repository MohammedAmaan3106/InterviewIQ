"""
Adaptive Engine Module.
Selects and adapts interview questions dynamically based on response length,
missing concrete examples, STAR structure gaps, and authoritative remaining time.
"""
from typing import Dict, Any, List, Optional
from backend.interview.question_bank import get_category_questions, ADAPTIVE_PROBES
from backend.speech.answer_relevance import AnswerRelevanceEvaluator

class AdaptiveEngine:
    def __init__(self, category: str = "General"):
        self.category = category
        self.question_bank = get_category_questions(category)
        self.current_bank_index = 0
        self.relevance_evaluator = AnswerRelevanceEvaluator()
        self.probed_example_for_current = False
        self.probed_action_for_current = False
        self.final_question_asked = False

    def get_current_question(self) -> Dict[str, str]:
        """Returns the active question."""
        if self.current_bank_index < len(self.question_bank):
            return self.question_bank[self.current_bank_index]
        return {
            "id": "wrap_up",
            "text": ADAPTIVE_PROBES["final_wrap_up"],
            "type": "final_wrap_up"
        }

    def decide_next_question(
        self,
        current_question_text: str,
        transcript: str,
        speaking_duration_seconds: float,
        time_remaining_seconds: float
    ) -> Dict[str, Any]:
        """
        Determines the next question or adaptive probe based on observed candidate answer.
        """
        eval_result = self.relevance_evaluator.evaluate(
            question=current_question_text,
            transcript=transcript,
            category=self.category
        )

        word_count = eval_result.get("word_count", 0)

        # 1. Authoritative Time Check: If time is running out (<= 15s) and final question hasn't been asked
        if time_remaining_seconds <= 15.0 and not self.final_question_asked:
            self.final_question_asked = True
            return {
                "id": f"adaptive_wrapup_{int(time_remaining_seconds)}",
                "text": ADAPTIVE_PROBES["final_wrap_up"],
                "type": "final_wrap_up",
                "reason": f"Time remaining is {int(time_remaining_seconds)}s: wrapping up gracefully."
            }

        # 2. Check for missing concrete example if answer is very brief (< 15 words)
        if word_count < 15 and not self.probed_example_for_current and not eval_result.get("has_example"):
            self.probed_example_for_current = True
            return {
                "id": f"probe_example_{self.current_bank_index}",
                "text": ADAPTIVE_PROBES["need_example"],
                "type": "probe_example",
                "reason": "Answer was brief and lacked a concrete example."
            }

        # 3. Check for STAR gap on challenge/project questions:
        current_q_type = self.question_bank[self.current_bank_index]["type"] if self.current_bank_index < len(self.question_bank) else ""
        if current_q_type in ["challenge", "conflict", "influence"] and word_count >= 10:
            if not eval_result.get("has_action") and not self.probed_action_for_current:
                self.probed_action_for_current = True
                return {
                    "id": f"probe_action_{self.current_bank_index}",
                    "text": ADAPTIVE_PROBES["need_action"],
                    "type": "probe_action",
                    "reason": "Candidate described the situation but omitted personal actions taken."
                }
            elif not eval_result.get("has_outcome") and self.probed_action_for_current:
                return {
                    "id": f"probe_outcome_{self.current_bank_index}",
                    "text": ADAPTIVE_PROBES["need_outcome"],
                    "type": "probe_outcome",
                    "reason": "Candidate detailed the actions taken but omitted the final outcome/results."
                }

        # 4. Standard progression to next question in bank
        self.current_bank_index += 1
        self.probed_example_for_current = False
        self.probed_action_for_current = False

        if self.current_bank_index < len(self.question_bank):
            next_q = self.question_bank[self.current_bank_index]
            return {
                "id": next_q["id"],
                "text": next_q["text"],
                "type": next_q["type"],
                "reason": "Candidate provided a structured response; advancing to next core question."
            }
        else:
            self.final_question_asked = True
            return {
                "id": "wrap_up",
                "text": ADAPTIVE_PROBES["final_wrap_up"],
                "type": "final_wrap_up",
                "reason": "Completed standard question sequence; wrapping up."
            }
