"""
Job fetchers for public, unauthenticated (or free-API-key) job board endpoints.

Deliberately does NOT scrape LinkedIn, Indeed, Glassdoor, or similar sites:
those require a login and their Terms of Service forbid automated access.
Scraping them is also unreliable (anti-bot detection, CAPTCHAs, layout churn)
and can get your account banned. Everything here talks to an API that is
either fully public or requires a free, self-service API key.

Each fetch_* function returns a list of models.Job.
"""
import os
import time
import html
import re
import logging

import requests

from src.models import Job

log = logging.getLogger("fetch_jobs")

USER_AGENT = "job-application-bot/1.0 (personal job search tool)"
REQUEST_TIMEOUT = 20


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _get(url: str, params: dict | None = None) -> requests.Response:
    resp = requests.get(
        url, params=params, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT
    )
    resp.raise_for_status()
    return resp


def fetch_remoteok(cfg: dict) -> list[Job]:
    """Public JSON feed of remote jobs. No auth required."""
    jobs: list[Job] = []
    try:
        data = _get(cfg["url"]).json()
    except Exception as exc:
        log.warning("remoteok fetch failed: %s", exc)
        return jobs

    for entry in data:
        # remoteok prefixes the feed with a legend/metadata object with no "id"
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        jobs.append(
            Job(
                source="remoteok",
                source_id=str(entry.get("id")),
                company=entry.get("company", "").strip(),
                title=entry.get("position", entry.get("title", "")).strip(),
                location=entry.get("location", "Remote") or "Remote",
                url=entry.get("url") or f"https://remoteok.com/l/{entry.get('id')}",
                description=_strip_html(entry.get("description", "")),
                posted_at=str(entry.get("date", "")),
            )
        )
    return jobs


def fetch_greenhouse(cfg: dict) -> list[Job]:
    """Greenhouse's public job-board API, used by companies to embed their own
    listings. Read-only, no auth. Docs: https://developers.greenhouse.io/job-board.html
    """
    jobs: list[Job] = []
    for token in cfg.get("companies", []):
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
        try:
            data = _get(url, params={"content": "true"}).json()
        except Exception as exc:
            log.warning("greenhouse fetch failed for %s: %s", token, exc)
            continue
        for entry in data.get("jobs", []):
            location = ""
            if isinstance(entry.get("location"), dict):
                location = entry["location"].get("name", "")
            jobs.append(
                Job(
                    source="greenhouse",
                    source_id=str(entry.get("id")),
                    company=token,
                    title=entry.get("title", "").strip(),
                    location=location,
                    url=entry.get("absolute_url", ""),
                    description=_strip_html(entry.get("content", "")),
                    posted_at=entry.get("updated_at", ""),
                )
            )
        time.sleep(0.2)  # be polite between companies
    return jobs


def fetch_lever(cfg: dict) -> list[Job]:
    """Lever's public postings API, same idea as Greenhouse's board API.
    Docs: https://github.com/lever/postings-api
    """
    jobs: list[Job] = []
    for token in cfg.get("companies", []):
        url = f"https://api.lever.co/v0/postings/{token}"
        try:
            data = _get(url, params={"mode": "json"}).json()
        except Exception as exc:
            log.warning("lever fetch failed for %s: %s", token, exc)
            continue
        for entry in data:
            categories = entry.get("categories", {}) or {}
            description = _strip_html(entry.get("descriptionPlain") or entry.get("description", ""))
            lists = entry.get("lists", []) or []
            extra = " ".join(_strip_html(item.get("content", "")) for item in lists)
            jobs.append(
                Job(
                    source="lever",
                    source_id=str(entry.get("id")),
                    company=token,
                    title=entry.get("text", "").strip(),
                    location=categories.get("location", ""),
                    url=entry.get("hostedUrl", ""),
                    description=f"{description} {extra}".strip(),
                    posted_at=str(entry.get("createdAt", "")),
                )
            )
        time.sleep(0.2)
    return jobs


def fetch_usajobs(cfg: dict) -> list[Job]:
    """USAJobs.gov public API - federal roles (network technician, IT specialist,
    help desk, etc.). Requires a free API key: https://developer.usajobs.gov/apirequest
    """
    jobs: list[Job] = []
    api_key = os.environ.get("USAJOBS_API_KEY")
    email = os.environ.get("USAJOBS_EMAIL")
    if not api_key or not email:
        log.info("usajobs enabled but USAJOBS_API_KEY/USAJOBS_EMAIL not set - skipping")
        return jobs

    headers = {
        "Host": "data.usajobs.gov",
        "User-Agent": email,
        "Authorization-Key": api_key,
    }
    for keyword in cfg.get("keywords", []):
        params = {"Keyword": keyword, "LocationName": cfg.get("location", "")}
        try:
            resp = requests.get(
                "https://data.usajobs.gov/api/search",
                headers=headers,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            log.warning("usajobs fetch failed for %r: %s", keyword, exc)
            continue

        for item in data.get("SearchResult", {}).get("SearchResultItems", []):
            d = item.get("MatchedObjectDescriptor", {})
            locations = d.get("PositionLocation", [])
            location = locations[0].get("LocationName", "") if locations else ""
            jobs.append(
                Job(
                    source="usajobs",
                    source_id=d.get("PositionID", d.get("MatchedObjectId", "")),
                    company=d.get("OrganizationName", "US Government"),
                    title=d.get("PositionTitle", "").strip(),
                    location=location,
                    url=d.get("PositionURI", ""),
                    description=_strip_html(
                        d.get("UserArea", {}).get("Details", {}).get("JobSummary", "")
                        or d.get("QualificationSummary", "")
                    ),
                    posted_at=d.get("PublicationStartDate", ""),
                )
            )
        time.sleep(0.3)
    return jobs


def fetch_adzuna(cfg: dict) -> list[Job]:
    """Adzuna's licensed job-search API - aggregates postings from many boards
    without scraping them directly. Requires a free app_id/app_key:
    https://developer.adzuna.com/
    """
    jobs: list[Job] = []
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        log.info("adzuna enabled but ADZUNA_APP_ID/ADZUNA_APP_KEY not set - skipping")
        return jobs

    country = cfg.get("country", "us")
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": cfg.get("what", ""),
        "where": cfg.get("where", ""),
        "max_days_old": cfg.get("max_days_old", 7),
        "content-type": "application/json",
        "results_per_page": 50,
    }
    try:
        data = _get(url, params=params).json()
    except Exception as exc:
        log.warning("adzuna fetch failed: %s", exc)
        return jobs

    for entry in data.get("results", []):
        jobs.append(
            Job(
                source="adzuna",
                source_id=str(entry.get("id")),
                company=(entry.get("company") or {}).get("display_name", ""),
                title=entry.get("title", "").strip(),
                location=(entry.get("location") or {}).get("display_name", ""),
                url=entry.get("redirect_url", ""),
                description=_strip_html(entry.get("description", "")),
                posted_at=entry.get("created", ""),
            )
        )
    return jobs


FETCHERS = {
    "remoteok": fetch_remoteok,
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "usajobs": fetch_usajobs,
    "adzuna": fetch_adzuna,
}


def fetch_all(sources_cfg: dict) -> list[Job]:
    """Run every enabled source in sources.yaml and return the combined job list."""
    all_jobs: list[Job] = []
    for name, fetcher in FETCHERS.items():
        cfg = sources_cfg.get(name, {})
        if not cfg.get("enabled"):
            continue
        log.info("fetching from %s ...", name)
        jobs = fetcher(cfg)
        log.info("  got %d jobs from %s", len(jobs), name)
        all_jobs.extend(jobs)
    return all_jobs
