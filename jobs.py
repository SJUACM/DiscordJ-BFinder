import json
import re
from datetime import datetime, timedelta

import requests

# Public GitHub files. We do not log into Jobright or LinkedIn.
JOBRIGHT_LISTS = [
    (
        "https://raw.githubusercontent.com/jobright-ai/2026-Software-Engineer-Internship/master/README.md",
        "Jobright",
        "internship",
    ),
    (
        "https://raw.githubusercontent.com/jobright-ai/2026-Data-Analysis-Internship/master/README.md",
        "Jobright",
        "internship",
    ),
    (
        "https://raw.githubusercontent.com/jobright-ai/2026-Software-Engineer-New-Grad/master/README.md",
        "Jobright",
        "job",
    ),
    (
        "https://raw.githubusercontent.com/jobright-ai/2026-Data-Analysis-New-Grad/master/README.md",
        "Jobright",
        "job",
    ),
]
SIMPLIFY_LISTS = [
    (
        "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/.github/scripts/listings.json",
        "Simplify",
        "internship",
    ),
    (
        "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json",
        "Simplify",
        "job",
    ),
]

# A listing has to be this new to be posted.
RECENT_DAYS = 14
INTERNSHIP_LIMIT = 3
JOB_LIMIT = 2

# Skip companies we do not want in the channel.
BLOCKED_COMPANIES = ["palantir"]

# Title phrases for the four fields the channel wants.
ROLE_PHRASES = [
    ("cyber", ["cyber", "information security", "security engineer", "security analyst", "appsec"]),
    ("ai", ["artificial intelligence", "machine learning", "ml engineer", "generative ai"]),
    ("data", ["data science", "data scientist", "data analyst", "data analysis", "data analytics", "data engineer"]),
    ("swe", ["software", "developer", "full stack", "full-stack", "frontend", "front-end", "backend", "back-end", "devops"]),
]


def get_text(url):
    headers = {"User-Agent": "acm-internship-bot"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def link_parts(cell):
    """Pull the visible name and the url out of a markdown link."""
    match = re.search(r"\[([^\]]+)\]\(([^)]+)\)", cell)
    if match is None:
        name = cell.replace("*", "").strip()
        return name, ""
    return match.group(1).strip(), match.group(2).strip()


def posted_time(text):
    """Turn a Jobright date like 'Nov 20' into a timestamp."""
    try:
        when = datetime.strptime(text.strip(), "%b %d")
    except ValueError:
        return 0
    when = when.replace(year=datetime.now().year)
    if when - datetime.now() > timedelta(days=1):
        when = when.replace(year=datetime.now().year - 1)
    return when.timestamp()


def is_nyc(location):
    text = location.lower().strip()
    # "New York, NY" is the city. "Liverpool, New York" is not.
    if text.startswith("new york"):
        return True
    phrases = [
        "nyc",
        "new york, ny",
        "new york ny",
        "manhattan",
        "brooklyn, ny",
        "queens, ny",
        "bronx, ny",
        "staten island",
        "long island city",
        "harlem",
    ]
    for phrase in phrases:
        if phrase in text:
            return True
    return False


def is_recent(posted):
    if not posted:
        return False
    age_days = (datetime.now().timestamp() - posted) / 86400
    return -1 <= age_days <= RECENT_DAYS


def jobs_from_jobright(text, source_name, kind):
    jobs = []
    last_company = ""

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if "---" in line or "Job Title" in line:
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3:
            continue

        company, _company_link = link_parts(cells[0])
        if company in ("", "↳"):
            company = last_company
        else:
            last_company = company

        title, link = link_parts(cells[1])
        if title == "" or link == "":
            continue
        if kind == "job" and "intern" in title.lower():
            continue

        posted = posted_time(cells[4]) if len(cells) >= 5 else 0
        jobs.append(
            {
                "company": company,
                "title": title,
                "location": cells[2],
                "link": link,
                "source": source_name,
                "kind": kind,
                "posted": posted,
            }
        )

    return jobs


def is_blocked(company):
    name = company.lower()
    for blocked in BLOCKED_COMPANIES:
        if blocked in name:
            return True
    return False


def role_category(title):
    lowered = title.lower()
    if lowered.startswith("ai ") or lowered.startswith("ai/") or " ai " in f" {lowered} ":
        return "ai"
    for category, phrases in ROLE_PHRASES:
        for phrase in phrases:
            if phrase in lowered:
                return category
    return ""


def jobs_from_simplify(text, source_name, kind):
    data = json.loads(text)
    if not isinstance(data, list):
        return []

    jobs = []
    for item in data:
        if not item.get("active") or not item.get("is_visible"):
            continue

        title = item.get("title") or ""
        link = item.get("url") or ""
        if link == "" or role_category(title) == "":
            continue
        if kind == "job" and "intern" in title.lower():
            continue

        places = item.get("locations") or []
        if isinstance(places, list):
            location = ", ".join(places)
        else:
            location = str(places)

        jobs.append(
            {
                "company": item.get("company_name") or "Unknown",
                "title": title,
                "location": location,
                "link": link,
                "source": source_name,
                "kind": kind,
                "posted": item.get("date_posted") or 0,
            }
        )

    return jobs


def get_all_jobs():
    found = []
    downloaded = False

    for url, source_name, kind in JOBRIGHT_LISTS:
        try:
            text = get_text(url)
            found.extend(jobs_from_jobright(text, source_name, kind))
            downloaded = True
        except Exception as error:
            print("Could not read Jobright list:", error)

    for url, source_name, kind in SIMPLIFY_LISTS:
        try:
            text = get_text(url)
            found.extend(jobs_from_simplify(text, source_name, kind))
            downloaded = True
        except Exception as error:
            print("Could not read Simplify list:", error)

    if not downloaded:
        return None

    # Same link on two lists should only be kept once.
    unique = []
    seen_links = set()
    for job in found:
        if job["link"] in seen_links:
            continue
        seen_links.add(job["link"])
        unique.append(job)
    return unique


def pick_mixed(all_jobs, seen, kind, limit):
    buckets = {"swe": [], "data": [], "ai": [], "cyber": []}
    for job in all_jobs:
        if job["kind"] != kind or job["link"] in seen or is_blocked(job["company"]):
            continue
        if not is_nyc(job["location"]) or not is_recent(job["posted"]):
            continue
        category = role_category(job["title"])
        if category == "":
            continue
        buckets[category].append(job)

    for items in buckets.values():
        items.sort(key=lambda job: job["posted"], reverse=True)

    # Rotate the starting field each hour so one field does not crowd out the others.
    order = ["swe", "data", "ai", "cyber"]
    start = datetime.now().hour % len(order)
    order = order[start:] + order[:start]

    picked = []
    used_links = set()
    for category in order:
        if len(picked) >= limit:
            break
        for job in buckets[category]:
            picked.append(job)
            used_links.add(job["link"])
            break

    rest = []
    for category in order:
        rest.extend(buckets[category])
    rest.sort(key=lambda job: job["posted"], reverse=True)
    for job in rest:
        if len(picked) >= limit:
            break
        if job["link"] not in used_links:
            picked.append(job)
            used_links.add(job["link"])
    return picked


def get_new_jobs(seen):
    all_jobs = get_all_jobs()
    if all_jobs is None:
        return None

    internships = pick_mixed(all_jobs, seen, "internship", INTERNSHIP_LIMIT)
    full_time = pick_mixed(all_jobs, seen, "job", JOB_LIMIT)
    return internships + full_time
