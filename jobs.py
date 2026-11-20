import json
import re

import requests

# Public GitHub files. We do not log into Jobright or LinkedIn.
JOBRIGHT_LISTS = [
    (
        "https://raw.githubusercontent.com/jobright-ai/2026-Software-Engineer-Internship/master/README.md",
        "Jobright",
    ),
    (
        "https://raw.githubusercontent.com/jobright-ai/2026-Data-Analysis-Internship/master/README.md",
        "Jobright",
    ),
]
SIMPLIFY_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/"
    "dev/.github/scripts/listings.json"
)

# Keep Simplify rows whose title looks like a CS internship.
CS_WORDS = [
    "software",
    "data",
    "machine learning",
    "cyber",
    "developer",
    "devops",
    "security",
    "artificial intelligence",
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


def jobs_from_jobright(text, source_name):
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

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": cells[2],
                "link": link,
                "source": source_name,
            }
        )

    return jobs


def is_cs_title(title):
    lowered = title.lower()
    for word in CS_WORDS:
        if word in lowered:
            return True
    # "AI Intern" does not contain the words above.
    if lowered.startswith("ai ") or " ai " in f" {lowered} ":
        return True
    return False


def jobs_from_simplify(text):
    data = json.loads(text)
    if not isinstance(data, list):
        return []

    jobs = []
    for item in data:
        if not item.get("active") or not item.get("is_visible"):
            continue

        title = item.get("title") or ""
        link = item.get("url") or ""
        if link == "" or not is_cs_title(title):
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
                "source": "Simplify",
            }
        )

    return jobs


def get_all_jobs():
    found = []
    downloaded = False

    for url, source_name in JOBRIGHT_LISTS:
        try:
            text = get_text(url)
            found.extend(jobs_from_jobright(text, source_name))
            downloaded = True
        except Exception as error:
            print("Could not read Jobright list:", error)

    try:
        text = get_text(SIMPLIFY_URL)
        found.extend(jobs_from_simplify(text))
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


def get_new_jobs(seen):
    all_jobs = get_all_jobs()
    if all_jobs is None:
        return None

    new_jobs = []
    for job in all_jobs:
        if job["link"] not in seen:
            new_jobs.append(job)
    return new_jobs
