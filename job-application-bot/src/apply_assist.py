"""
Semi-automated "apply assist": opens each READY_TO_APPLY posting in a real,
visible browser window, tries to pre-fill the common fields (name, email,
phone) and attach the correct resume, then PAUSES for you to review, answer
any custom questions, and click submit yourself.

Why it doesn't click "submit" for you:
  - Most ATS forms have custom screening questions (work authorization,
    salary expectations, etc.) that a script can't answer correctly on your
    behalf.
  - Fully autonomous submission on job boards commonly violates their Terms
    of Service and can trigger anti-bot detection / get you rate-limited or
    banned - not worth the risk for what's ultimately a few seconds of
    clicking.
  - You should look at every application before it goes out; "spray and
    pray" applications tend to perform worse than a handful of tailored,
    reviewed ones.

This only targets Greenhouse and Lever postings, since their embedded
application forms have a fairly predictable structure. Everything else in
your tracker (RemoteOK, USAJobs, Adzuna-sourced listings on arbitrary
company sites) gets skipped here - use the generated application package
(resume + cover letter in output/applications/<job>/) to apply manually.
"""
import logging
from pathlib import Path

from src import tracker

log = logging.getLogger("apply_assist")

SUPPORTED_SOURCES = {"greenhouse", "lever"}

# Candidate CSS/label selectors to try, in order, for each field. Real forms
# vary (companies customize Greenhouse forms especially), so we try several
# strategies and silently move on if none match - better to fill 3 of 4
# fields than to crash on the first mismatch.
FIELD_SELECTORS = {
    "first_name": ["#first_name", "input[name='first_name']", "input[autocomplete='given-name']"],
    "last_name": ["#last_name", "input[name='last_name']", "input[autocomplete='family-name']"],
    "full_name": ["input[name='name']", "#name-input"],
    "email": ["#email", "input[name='email']", "input[type='email']"],
    "phone": ["#phone", "input[name='phone']", "input[type='tel']"],
}

FILE_INPUT_SELECTORS = ["input[type='file']"]


def _try_fill(page, selectors, value):
    if not value:
        return False
    for sel in selectors:
        try:
            locator = page.locator(sel).first
            if locator.count() > 0:
                locator.fill(value)
                return True
        except Exception:
            continue
    return False


def _try_upload(page, selectors, file_path: Path):
    if not file_path.exists():
        return False
    for sel in selectors:
        try:
            locator = page.locator(sel).first
            if locator.count() > 0:
                locator.set_input_files(str(file_path))
                return True
        except Exception:
            continue
    return False


def prefill_form(page, candidate_cfg: dict, resume_path: Path) -> None:
    name_parts = candidate_cfg["name"].split(maxsplit=1)
    first, last = (name_parts + [""])[:2]

    filled_first = _try_fill(page, FIELD_SELECTORS["first_name"], first)
    filled_last = _try_fill(page, FIELD_SELECTORS["last_name"], last)
    if not (filled_first and filled_last):
        _try_fill(page, FIELD_SELECTORS["full_name"], candidate_cfg["name"])

    _try_fill(page, FIELD_SELECTORS["email"], candidate_cfg["email"])
    _try_fill(page, FIELD_SELECTORS["phone"], candidate_cfg["phone"])
    _try_upload(page, FILE_INPUT_SELECTORS, resume_path)


def run_assist(tracker_path: Path, resumes_dir: Path, candidate_cfg: dict, limit: int = 5) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright isn't installed. Run:\n  pip install playwright\n  playwright install chromium")
        return

    rows = tracker.load(tracker_path)
    targets = [
        row
        for row in rows.values()
        if row["status"] == "READY_TO_APPLY" and row["source"] in SUPPORTED_SOURCES
    ][:limit]

    if not targets:
        print("No READY_TO_APPLY Greenhouse/Lever jobs found in the tracker.")
        print("(Other sources need to be applied to manually - see output/applications/.)")
        return

    print(f"Opening {len(targets)} application(s) for review. Nothing is submitted automatically.\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        for row in targets:
            resume_path = resumes_dir / row["resume_used"]
            page = browser.new_page()
            print(f"\n--- {row['company']} - {row['title']} ---\n{row['url']}")
            try:
                page.goto(row["url"], wait_until="domcontentloaded", timeout=30000)
                prefill_form(page, candidate_cfg, resume_path)
            except Exception as exc:
                log.warning("could not fully load/prefill %s: %s", row["url"], exc)
                print(f"  (couldn't auto-fill everything - {exc}; fill it in manually below)")

            print("  Review the pre-filled fields, answer any custom questions,")
            print("  and submit the application yourself in the browser window.")
            outcome = input("  Mark as [a]pplied, [s]kip, or [q]uit assist? ").strip().lower()
            page.close()

            if outcome == "a":
                row["status"] = "APPLIED"
                from datetime import date
                row["applied_date"] = date.today().isoformat()
            elif outcome == "s":
                row["status"] = "SKIPPED"
            tracker.save(tracker_path, rows)

            if outcome == "q":
                break
        browser.close()

    print("\nDone. Tracker updated:", tracker_path)
