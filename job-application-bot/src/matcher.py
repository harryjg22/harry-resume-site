"""
Scores each job against both resume tracks (hardware_it vs software_development),
picks whichever track the job actually is, and produces a 0-100 qualification
score plus matched/missing skills so you can see *why* a job was ranked the
way it was.

This is intentionally simple keyword/weight scoring, not an LLM call per job -
it's fast, free, deterministic, and easy for you to tune by editing
config/skills.yaml.
"""
import re

from src.models import Job, MatchResult


def _pattern_for(name: str, aliases: list[str] | None) -> re.Pattern:
    terms = [name] + (aliases or [])
    escaped = [re.escape(t) for t in terms]
    # word-boundary-ish match; escape handles things like "C++" and "Cat-5e"
    return re.compile(r"(?<![A-Za-z0-9])(" + "|".join(escaped) + r")(?![A-Za-z0-9])", re.IGNORECASE)


class Track:
    def __init__(self, key: str, cfg: dict):
        self.key = key
        self.resume_file = cfg["resume_file"]
        self.cover_letter_template = cfg["cover_letter_template"]
        self.title_keywords = [kw.lower() for kw in cfg.get("title_keywords", [])]
        self.skills = []
        for s in cfg.get("skills", []):
            self.skills.append(
                {
                    "name": s["name"],
                    "weight": s.get("weight", 1),
                    "pattern": _pattern_for(s["name"], s.get("aliases")),
                }
            )
        self.max_weight = sum(s["weight"] for s in self.skills) or 1


class Matcher:
    def __init__(self, skills_cfg: dict, candidate_cfg: dict):
        self.tracks = {
            key: Track(key, cfg) for key, cfg in skills_cfg["tracks"].items()
        }
        seniority = skills_cfg.get("seniority", {})
        self.favorable_terms = [t.lower() for t in seniority.get("favorable_title_terms", [])]
        self.unfavorable_terms = [t.lower() for t in seniority.get("unfavorable_title_terms", [])]
        self.favorable_bonus = seniority.get("favorable_bonus", 0)
        self.unfavorable_penalty = seniority.get("unfavorable_penalty", 0)
        self.max_years_ok = seniority.get("max_years_ok", 2)
        self.years_penalty_per_year_over = seniority.get("years_penalty_per_year_over", 0)

        self.min_qualified = candidate_cfg.get("min_qualified_score", 55)
        self.min_close = candidate_cfg.get("min_close_score", 35)

        self._years_re = re.compile(r"(\d{1,2})\+?\s*(?:years|yrs)", re.IGNORECASE)

    def _skill_score(self, track: Track, text: str):
        matched, missing = [], []
        raw = 0
        for skill in track.skills:
            if skill["pattern"].search(text):
                matched.append(skill["name"])
                raw += skill["weight"]
            else:
                missing.append(skill["name"])
        normalized = 100.0 * raw / track.max_weight
        # sort missing by weight desc so the most important gaps show up first
        weight_by_name = {s["name"]: s["weight"] for s in track.skills}
        missing.sort(key=lambda n: -weight_by_name[n])
        return normalized, matched, missing

    def _title_bonus(self, track: Track, title_lower: str) -> float:
        return 25.0 if any(kw in title_lower for kw in track.title_keywords) else 0.0

    def _seniority_adjustment(self, title_lower: str, description: str):
        adj = 0.0
        notes = []
        if any(t in title_lower for t in self.favorable_terms):
            adj += self.favorable_bonus
            notes.append("entry-level-friendly title")
        if any(t in title_lower for t in self.unfavorable_terms):
            adj -= self.unfavorable_penalty
            notes.append("senior-sounding title")

        years_found = [int(y) for y in self._years_re.findall(description)]
        if years_found:
            worst = max(years_found)
            if worst > self.max_years_ok:
                penalty = (worst - self.max_years_ok) * self.years_penalty_per_year_over
                adj -= penalty
                notes.append(f"posting asks for {worst}+ years experience")
        return adj, notes

    def score(self, job: Job) -> MatchResult:
        title_lower = job.title.lower()
        text = f"{job.title} {job.description}"

        best_track_key, best_raw_skill_score, best_payload = None, -1.0, None
        for key, track in self.tracks.items():
            skill_score, matched, missing = self._skill_score(track, text)
            title_bonus = self._title_bonus(track, title_lower)
            # classification is driven mostly by which track's vocabulary actually
            # shows up (skills + title), not just raw skill overlap
            classification_signal = skill_score + title_bonus
            if classification_signal > best_raw_skill_score:
                best_raw_skill_score = classification_signal
                best_track_key = key
                best_payload = (skill_score, title_bonus, matched, missing)

        skill_score, title_bonus, matched, missing = best_payload
        seniority_adj, notes = self._seniority_adjustment(title_lower, job.description)

        # weight: skills matter most, title match is a strong secondary signal
        overall = 0.75 * skill_score + title_bonus + seniority_adj
        overall = max(0.0, min(100.0, overall))

        if overall >= self.min_qualified:
            status = "qualified"
        elif overall >= self.min_close:
            status = "close"
        else:
            status = "skipped"

        return MatchResult(
            job=job,
            track=best_track_key,
            score=round(overall, 1),
            matched_skills=matched,
            missing_skills=missing[:6],
            notes=notes,
            status=status,
        )

    def score_all(self, jobs: list[Job]) -> list[MatchResult]:
        return sorted((self.score(j) for j in jobs), key=lambda r: -r.score)
