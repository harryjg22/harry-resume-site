"""
CSV-backed application tracker. Acts as the single source of truth for what
you've found, what's ready to apply to, and what you've actually applied to -
so re-running `find` never creates duplicate entries for the same posting.

You're expected to hand-edit the status column (or use apply_assist.py, which
updates it for you) as you move jobs through your pipeline:
  READY_TO_APPLY -> APPLIED -> INTERVIEW / REJECTED / OFFER
  CLOSE_MATCH is a lower-confidence bucket for manual review.
  SKIPPED means the matcher scored it too low to bother with.
"""
import csv
from datetime import date
from pathlib import Path

from src.models import MatchResult

FIELDNAMES = [
    "dedup_key",
    "date_found",
    "source",
    "company",
    "title",
    "location",
    "url",
    "track",
    "resume_used",
    "score",
    "status",
    "matched_skills",
    "missing_skills",
    "notes",
    "applied_date",
    "application_folder",
]


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {row["dedup_key"]: row for row in csv.DictReader(f)}


def save(path: Path, rows: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows.values():
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})


def upsert(
    path: Path,
    results: list[MatchResult],
    resume_file_by_track: dict,
    application_folder_by_key: dict | None = None,
) -> tuple[dict, int]:
    """Merge new match results into the tracker CSV. Existing rows (already
    seen postings) are left untouched so manual status edits aren't clobbered.
    Returns (updated_rows, num_new_rows).
    """
    rows = load(path)
    new_count = 0
    application_folder_by_key = application_folder_by_key or {}

    for result in results:
        if result.status == "skipped":
            continue
        key = result.job.dedup_key
        if key in rows:
            continue

        rows[key] = {
            "dedup_key": key,
            "date_found": date.today().isoformat(),
            "source": result.job.source,
            "company": result.job.company,
            "title": result.job.title,
            "location": result.job.location,
            "url": result.job.url,
            "track": result.track,
            "resume_used": resume_file_by_track.get(result.track, ""),
            "score": result.score,
            "status": "READY_TO_APPLY" if result.status == "qualified" else "CLOSE_MATCH",
            "matched_skills": "; ".join(result.matched_skills),
            "missing_skills": "; ".join(result.missing_skills),
            "notes": "; ".join(result.notes),
            "applied_date": "",
            "application_folder": application_folder_by_key.get(key, ""),
        }
        new_count += 1

    save(path, rows)
    return rows, new_count


def summary(rows: dict) -> dict:
    counts: dict[str, int] = {}
    for row in rows.values():
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return counts
