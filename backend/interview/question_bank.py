"""
Question Bank Module.
Deterministic, local question repository organized by interview categories.
Guaranteed working offline fallback without requiring any external cloud APIs.
"""
from typing import List, Dict

CATEGORIES = ["General", "HR", "Communication", "Technical Fundamentals"]

QUESTION_BANKS: Dict[str, List[Dict[str, str]]] = {
    "General": [
        {
            "id": "gen_1",
            "text": "Tell me about yourself and what drives your professional work.",
            "type": "opening"
        },
        {
            "id": "gen_2",
            "text": "What is one technical or professional skill you are most proud of, and why?",
            "type": "skill"
        },
        {
            "id": "gen_3",
            "text": "Describe a difficult challenge you solved recently. How did you tackle it?",
            "type": "challenge"
        },
        {
            "id": "gen_4",
            "text": "Why should a team choose you for this role over other qualified candidates?",
            "type": "value_prop"
        }
    ],
    "HR": [
        {
            "id": "hr_1",
            "text": "Tell me about yourself and your typical work style in a collaborative environment.",
            "type": "opening"
        },
        {
            "id": "hr_2",
            "text": "Describe a time when you received constructive feedback. How did you respond?",
            "type": "challenge"
        },
        {
            "id": "hr_3",
            "text": "Tell me about a situation where you had a disagreement with a team member.",
            "type": "conflict"
        },
        {
            "id": "hr_4",
            "text": "Why should someone choose you for a team that values high accountability?",
            "type": "value_prop"
        }
    ],
    "Communication": [
        {
            "id": "comm_1",
            "text": "Tell me about yourself and how you approach explaining complex ideas to others.",
            "type": "opening"
        },
        {
            "id": "comm_2",
            "text": "Describe a project where you had to persuade stakeholders or team members.",
            "type": "influence"
        },
        {
            "id": "comm_3",
            "text": "Tell me about a time when communication broke down on a project and how you resolved it.",
            "type": "challenge"
        },
        {
            "id": "comm_4",
            "text": "What is one communication skill you are proud of developing over your career?",
            "type": "skill"
        }
    ],
    "Technical Fundamentals": [
        {
            "id": "tech_1",
            "text": "Tell me about yourself and your background in software engineering.",
            "type": "opening"
        },
        {
            "id": "tech_2",
            "text": "What is one core technical skill or technology you are most proficient in?",
            "type": "skill"
        },
        {
            "id": "tech_3",
            "text": "Describe a complex technical bug or architecture problem you resolved.",
            "type": "challenge"
        },
        {
            "id": "tech_4",
            "text": "Why should an engineering team trust your technical judgment on key decisions?",
            "type": "value_prop"
        }
    ]
}

ADAPTIVE_PROBES = {
    "need_example": "Could you give a concrete, specific example to illustrate that point?",
    "need_action": "What specific action did you personally take to address that situation?",
    "need_outcome": "What was the final outcome or impact after you implemented that solution?",
    "final_wrap_up": "In our final moments, what is the single key takeaway you'd like to leave with us?"
}

def get_initial_question(category: str = "General") -> Dict[str, str]:
    """Returns the first question for the selected category."""
    bank = QUESTION_BANKS.get(category, QUESTION_BANKS["General"])
    return bank[0]

def get_category_questions(category: str = "General") -> List[Dict[str, str]]:
    """Returns the full sequence of structured questions for the category."""
    return QUESTION_BANKS.get(category, QUESTION_BANKS["General"])
