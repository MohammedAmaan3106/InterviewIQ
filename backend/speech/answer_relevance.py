"""
Answer Relevance Evaluator Module.
Applies transparent, documented heuristics to assess answer completeness,
concrete example specificity, and STAR structure alignment.
All scores are clearly labeled as heuristic estimates.
"""
import re
from typing import Dict, Any, List

EXAMPLE_KEYWORDS = [
    "for example", "for instance", "such as", "specifically",
    "particular project", "one project", "client", "customer",
    "production", "codebase", "architecture", "designed", "implemented",
    "implement", "system", "service", "application", "database", "feature",
    "solution", "pipeline", "platform"
]

STAR_SITUATION_KEYWORDS = [
    "situation", "when i was", "at my previous", "in my role",
    "our team", "project", "problem", "challenge", "issue", "bug",
    "deadline", "conflict", "requirement", "goal"
]

STAR_ACTION_KEYWORDS = [
    "i decided", "i built", "i developed", "i created", "i designed",
    "i investigated", "i refactored", "i resolved", "i led", "i stepped in",
    "i implemented", "i communicated", "my approach was", "i analyzed"
]

STAR_RESULT_KEYWORDS = [
    "result", "outcome", "impact", "reduced", "increased", "improved",
    "delivered", "succeeded", "learned", "achieved", "saved", "prevented"
]

CATEGORY_KEYWORDS = {
    "General": ["skill", "experience", "strength", "growth", "challenge", "collaborate", "value", "role"],
    "HR": ["team", "feedback", "culture", "conflict", "collaborate", "mentor", "perspective", "listen"],
    "Communication": ["explain", "simplify", "stakeholder", "presentation", "clarity", "aligned", "bridge"],
    "Technical Fundamentals": ["architecture", "code", "latency", "system", "database", "api", "debug", "test", "scale"]
}

class AnswerRelevanceEvaluator:
    def evaluate(self, question: str, transcript: str, category: str = "General") -> Dict[str, Any]:
        """
        Evaluates an answer against the question using transparent local heuristics.
        """
        text = transcript.strip().lower()
        words = re.findall(r"\b[a-zA-Z0-9']+\b", text)
        word_count = len(words)

        if word_count < 5:
            return {
                "measured": False,
                "score": None,
                "label": "Answer too brief to evaluate",
                "has_example": False,
                "has_action": False,
                "has_outcome": False,
                "evidence": ["Candidate provided fewer than 5 words."],
                "missing_elements": ["Substantive response", "Concrete example"]
            }

        evidence: List[str] = []
        missing: List[str] = []

        # 1. Depth & Length (up to 30 points)
        if word_count >= 40:
            length_score = 30.0
            evidence.append(f"Substantive response length ({word_count} words).")
        elif word_count >= 20:
            length_score = 22.0
            evidence.append(f"Moderate response length ({word_count} words).")
        elif word_count >= 12:
            length_score = 14.0
            missing.append("Additional elaboration")
        else:
            length_score = 7.0
            missing.append("Substantive depth (very brief answer)")

        # 2. Concrete Example Specificity (up to 25 points)
        found_examples = [kw for kw in EXAMPLE_KEYWORDS if kw in text]
        has_example = bool(len(found_examples) > 0)
        if has_example:
            example_score = 25.0
            evidence.append(f"Referenced concrete instance or project: '{found_examples[0]}'.")
        else:
            example_score = 10.0
            missing.append("Concrete illustrative example")

        # 3. STAR Structure (up to 30 points: 10 per stage)
        has_situation = any(kw in text for kw in STAR_SITUATION_KEYWORDS)
        has_action = any(kw in text for kw in STAR_ACTION_KEYWORDS)
        has_outcome = any(kw in text for kw in STAR_RESULT_KEYWORDS)

        star_score = 0.0
        if has_situation:
            star_score += 10.0
        if has_action:
            star_score += 12.0
            evidence.append("Identified personal action taken.")
        else:
            missing.append("Personal action details ('I designed / I resolved')")

        if has_outcome:
            star_score += 8.0
            evidence.append("Mentioned outcome or impact achieved.")
        else:
            missing.append("Quantifiable result or outcome")

        # 4. Domain & Category Terminology (up to 15 points)
        target_kws = CATEGORY_KEYWORDS.get(category, CATEGORY_KEYWORDS["General"])
        found_kws = [kw for kw in target_kws if kw in text]
        domain_score = min(15.0, len(found_kws) * 5.0)
        if found_kws:
            evidence.append(f"Used relevant domain terminology: {', '.join(found_kws[:3])}.")

        total_score = round(min(100.0, length_score + example_score + star_score + domain_score), 1)

        # Quality label
        if total_score >= 80.0:
            label = "Strong, structured response"
        elif total_score >= 60.0:
            label = "Competent answer with growth areas"
        else:
            label = "Developing answer needing more structure"

        return {
            "measured": True,
            "score": total_score,
            "label": label,
            "word_count": word_count,
            "has_example": has_example,
            "has_action": has_action,
            "has_outcome": has_outcome,
            "evidence": evidence,
            "missing_elements": missing
        }
