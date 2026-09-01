#!/usr/bin/env python3
"""
Job application automation - entry point.

Usage:
    python cli.py find              Fetch jobs, score them, generate application
                                     packages for qualified/close matches, and
                                     update the tracker.
    python cli.py find --dry-run    Same, but score fixture data instead of
                                     hitting real job APIs (useful for testing
                                     config changes, or when your network
                                     blocks the job board APIs).
    python cli.py status            Print a summary of the tracker.
    python cli.py assist            Launch the semi-automated browser assist
                                     for READY_TO_APPLY Greenhouse/Lever jobs
                                     (see src/apply_assist.py). Opens each
                                     application in a real browser window,
                                     pre-fills your info and uploads the right
                                     resume, and pauses for you to review and
                                     submit yourself.

See README.md for setup (API keys, dependencies) and how the scoring works.
"""
import argparse
import json
import logging
import re
import sys
from datetime import date
from pathlib import Path

import yaml
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.fetch_jobs import fetch_all
from src.matcher import Matcher
from src.cover_letter import generate as generate_cover_letter
from src.models import Job
from src import tracker

ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "config"
OUTPUT_DIR = ROOT / "output"
TRACKER_PATH = OUTPUT_DIR / "applications.csv"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("cli")


def load_yaml(name: str) -> dict:
    with (CONFIG_DIR / name).open() as f:
        return yaml.safe_load(f)


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:60] or "job"


def load_fixture_jobs() -> list[Job]:
    fixture_path = ROOT / "tests" / "fixtures" / "sample_jobs.json"
    data = json.loads(fixture_path.read_text())
    return [Job(**entry) for entry in data]


def build_packages(results, candidate_cfg, skills_cfg) -> dict:
    """Write a per-job folder with the job description, the correct resume,
    and a drafted cover letter for every qualified/close match. Returns a
    dict of dedup_key -> folder path for the tracker.
    """
    folder_by_key = {}
    apps_dir = OUTPUT_DIR / "applications"

    for result in results:
        if result.status == "skipped":
            continue

        folder_name = f"{date.today().isoformat()}_{slugify(result.job.company)}_{slugify(result.job.title)}"
        folder = apps_dir / folder_name
        folder.mkdir(parents=True, exist_ok=True)

        track_cfg = skills_cfg["tracks"][result.track]
        resume_src = ROOT / "resumes" / track_cfg["resume_file"]
        resume_dst = folder / track_cfg["resume_file"]
        if resume_src.exists():
            resume_dst.write_bytes(resume_src.read_bytes())

        (folder / "cover_letter.txt").write_text(
            generate_cover_letter(result, candidate_cfg)
        )

        (folder / "job.json").write_text(
            json.dumps(
                {
                    "company": result.job.company,
                    "title": result.job.title,
                    "location": result.job.location,
                    "url": result.job.url,
                    "source": result.job.source,
                    "track": result.track,
                    "score": result.score,
                    "status": result.status,
                    "matched_skills": result.matched_skills,
                    "missing_skills": result.missing_skills,
                    "notes": result.notes,
                    "description": result.job.description,
                },
                indent=2,
            )
        )
        folder_by_key[result.job.dedup_key] = str(folder.relative_to(ROOT))

    return folder_by_key


def cmd_find(args):
    load_dotenv(ROOT / ".env")
    candidate_cfg = load_yaml("candidate.yaml")
    skills_cfg = load_yaml("skills.yaml")

    if args.dry_run:
        log.info("dry run: scoring fixture jobs instead of calling live job APIs")
        jobs = load_fixture_jobs()
    else:
        sources_cfg = load_yaml("sources.yaml")
        jobs = fetch_all(sources_cfg)

    log.info("scoring %d jobs against both resumes", len(jobs))
    matcher = Matcher(skills_cfg, candidate_cfg)
    results = matcher.score_all(jobs)

    qualified = [r for r in results if r.status == "qualified"]
    close = [r for r in results if r.status == "close"]
    log.info("%d qualified, %d close matches, %d skipped", len(qualified), len(close), len(results) - len(qualified) - len(close))

    folder_by_key = build_packages(qualified + close, candidate_cfg, skills_cfg)

    resume_file_by_track = {
        key: cfg["resume_file"] for key, cfg in skills_cfg["tracks"].items()
    }
    rows, new_count = tracker.upsert(TRACKER_PATH, results, resume_file_by_track, folder_by_key)
    log.info("added %d new rows to %s", new_count, TRACKER_PATH)

    print("\nTop matches this run:")
    for r in (qualified + close)[:15]:
        print(f"  [{r.score:5.1f}] {r.status:9s} {r.track:22s} {r.job.company} - {r.job.title}")

    print(f"\nApplication packages written to: {OUTPUT_DIR / 'applications'}")
    print(f"Tracker: {TRACKER_PATH}")


def cmd_status(_args):
    rows = tracker.load(TRACKER_PATH)
    if not rows:
        print("No tracker data yet. Run `python cli.py find` first.")
        return
    counts = tracker.summary(rows)
    print(f"Tracker: {TRACKER_PATH} ({len(rows)} total postings)")
    for status, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {status:15s} {n}")


def cmd_assist(args):
    from src.apply_assist import run_assist

    load_dotenv(ROOT / ".env")
    candidate_cfg = load_yaml("candidate.yaml")
    run_assist(TRACKER_PATH, ROOT / "resumes", candidate_cfg, limit=args.limit)


def main():
    parser = argparse.ArgumentParser(description="Job application automation")
    sub = parser.add_subparsers(dest="command", required=True)

    p_find = sub.add_parser("find", help="fetch, score, and package qualified jobs")
    p_find.add_argument("--dry-run", action="store_true", help="use fixture jobs instead of live APIs")
    p_find.set_defaults(func=cmd_find)

    p_status = sub.add_parser("status", help="show tracker summary")
    p_status.set_defaults(func=cmd_status)

    p_assist = sub.add_parser("assist", help="semi-automated browser apply assist")
    p_assist.add_argument("--limit", type=int, default=5, help="max jobs to open this run")
    p_assist.set_defaults(func=cmd_assist)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
