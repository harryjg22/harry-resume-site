from datetime import date
from pathlib import Path

from src.models import MatchResult

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def generate(result: MatchResult, candidate_cfg: dict) -> str:
    track_template = {
        "hardware_it": "cover_letter_hardware.txt",
        "software_development": "cover_letter_software.txt",
    }[result.track]

    template = (TEMPLATES_DIR / track_template).read_text()

    matched = result.matched_skills[:8] or ["a strong overlap with the role's requirements"]
    matched_skills_str = ", ".join(matched)

    return template.format(
        date=date.today().strftime("%B %d, %Y"),
        company=result.job.company or "your team",
        title=result.job.title,
        matched_skills=matched_skills_str,
        name=candidate_cfg["name"],
        email=candidate_cfg["email"],
        phone=candidate_cfg["phone"],
    )
