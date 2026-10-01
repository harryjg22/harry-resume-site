# Job Application Bot

Finds job postings, scores them against **both** of your resumes (Hardware/IT
and Software Development), picks whichever one actually fits, and generates a
ready-to-send application package (correct resume + a tailored cover letter)
for every job you're qualified for or close to qualified for. It also tracks
everything in a CSV so nothing gets applied to twice.

## What this does and doesn't automate

**Automated:**
- Pulling job postings from public/free job-board APIs.
- Scoring every posting against your Hardware/IT resume *and* your Software
  Development resume, and classifying which track it belongs to.
- Picking the right resume and drafting a tailored cover letter.
- Tracking what you've found/applied to in `output/applications.csv`.

**Not automated (on purpose):** actually clicking "Submit" on a job board.
Two reasons:
1. Sites like LinkedIn and Indeed require login and their Terms of Service
   prohibit automated/bot access - scraping or auto-submitting there risks
   your account getting banned, and reliably works around anti-bot
   protections is not something this tool does.
2. Most applications have custom screening questions (work authorization,
   compensation expectations, etc.) that only you can answer correctly.

For Greenhouse and Lever postings (which have fairly predictable embedded
forms), `python cli.py assist` opens each one in a real browser window,
pre-fills your name/email/phone and uploads the right resume, and then pauses
for **you** to review, answer any extra questions, and submit it yourself.
Everything else gets a complete application package written to
`output/applications/<job>/` (resume + cover letter + job details) for you to
paste into whatever site the job is posted on.

## Setup

```bash
cd job-application-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium   # only needed for `cli.py assist`
cp .env.example .env          # fill in API keys for any sources you enable
```

Your two resumes are already in `resumes/`:
- `resumes/hardware_it.pdf` - IT support / network technician track
- `resumes/software_development.pdf` - software engineering track

Replace them with updated versions whenever your resume changes; the content
used for *matching/scoring* lives separately in `config/skills.yaml` (see
below), so update that too if your skills change.

## Configure

- **`config/candidate.yaml`** - your contact info and the score thresholds
  that decide "qualified" vs "close match" vs "skip".
- **`config/skills.yaml`** - the keyword/weight lists used to classify a job
  as Hardware/IT vs Software Development and to score how qualified you are.
  This is the main file to tune over time.
- **`config/sources.yaml`** - which job sources to pull from. Enabled by
  default with no API key required:
  - **RemoteOK** - public JSON feed of remote jobs.
  - **Greenhouse** - add company board tokens (from
    `boards.greenhouse.io/<token>`) for companies you're targeting.
  - **Lever** - same idea, tokens from `jobs.lever.co/<token>`.

  Optional, need a free API key (put it in `.env`):
  - **USAJobs** - federal help-desk/network-technician/IT roles.
    https://developer.usajobs.gov/apirequest
  - **Adzuna** - aggregates postings from many boards via a licensed API
    (not scraping). https://developer.adzuna.com/

  Note: none of these sources scrape LinkedIn or Indeed directly - see
  "What this does and doesn't automate" above for why.

## Run

```bash
# Fetch real jobs, score them, generate application packages:
python cli.py find

# Test the whole pipeline against sample data (no network calls) - useful
# after editing config/skills.yaml to see how scores change:
python cli.py find --dry-run

# See where things stand:
python cli.py status

# Semi-automated browser assist for Greenhouse/Lever postings marked
# READY_TO_APPLY:
python cli.py assist
```

Each run of `find` adds new postings to `output/applications.csv` without
touching rows it's already seen, so you can safely re-run it daily/weekly (a
cron job, a scheduled GitHub Action, etc.) to keep discovering new postings.

## How scoring works

For every job, `src/matcher.py`:
1. Checks the title and description against the keyword list for **both**
   tracks in `config/skills.yaml`.
2. Whichever track scores higher becomes the job's classification
   (`hardware_it` or `software_development`) - that's the resume that gets
   used.
3. Combines: a weighted skill-overlap score (0-75 pts) + a title-keyword
   match bonus (+25 if the title itself matches the track, e.g. "Help Desk
   Technician" or "Software Engineer") + a seniority adjustment (bonus for
   junior/entry/associate-sounding titles, penalty for senior/staff/lead
   titles or postings asking for many more years of experience than you
   have).
4. Buckets the result: `qualified` (>= `min_qualified_score`), `close`
   (>= `min_close_score`), or skipped entirely.

Tune the thresholds in `config/candidate.yaml` and the keyword weights in
`config/skills.yaml` as you see how it performs on real postings.

## Tracker columns (`output/applications.csv`)

| column | meaning |
|---|---|
| `status` | `READY_TO_APPLY`, `CLOSE_MATCH`, `APPLIED`, `SKIPPED`, or any status you set yourself (`INTERVIEW`, `REJECTED`, `OFFER`, ...) |
| `track` / `resume_used` | which resume was matched/selected |
| `score` | 0-100 qualification score |
| `application_folder` | path to the generated resume + cover letter for this job |

Edit this file by hand as applications progress - `find` will never overwrite
an existing row, and `assist` only updates `status`/`applied_date` for the
rows you act on.

## A note on "mass applying"

This tool is built to help you apply to a *lot* of relevant postings quickly
without wasting time on ones you're clearly not qualified for or blasting out
generic applications - not to submit hundreds of untailored applications
with no human review. Untargeted spam applications tend to get auto-rejected
by ATS keyword filters anyway, and can flag your account on job boards that
detect bot traffic. Review the generated cover letters before sending;
they're a solid first draft, not guaranteed to be perfect for every posting.
