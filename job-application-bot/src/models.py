from dataclasses import dataclass, field


@dataclass
class Job:
    source: str          # "remoteok", "greenhouse", "lever", "usajobs", "adzuna"
    source_id: str        # id unique within the source, used for dedup
    company: str
    title: str
    location: str
    url: str
    description: str
    posted_at: str = ""

    @property
    def dedup_key(self) -> str:
        return f"{self.source}:{self.source_id}"


@dataclass
class MatchResult:
    job: Job
    track: str                 # "hardware_it" or "software_development"
    score: float                # 0-100 overall qualification score
    matched_skills: list = field(default_factory=list)
    missing_skills: list = field(default_factory=list)
    notes: list = field(default_factory=list)   # e.g. seniority flags
    status: str = ""            # "qualified" | "close" | "skipped"
