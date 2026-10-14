"""Refresh the light/dark profile cards while preserving the ASCII portrait.

Counts come from GitHub; BuildWithMe-UI is the owner's chosen featured repo.
The contribution sparkline is deliberately omitted.
"""
import calendar
import os
from datetime import date, datetime, timezone
import xml.etree.ElementTree as ET

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
FONT = "'Consolas', 'Menlo', 'DejaVu Sans Mono', monospace"


def account_age(created_at, today):
    start = date.fromisoformat(created_at[:10])
    months = (today.year - start.year) * 12 + today.month - start.month
    if today.day < start.day:
        months -= 1
    year = start.year + (start.month - 1 + months) // 12
    month = (start.month - 1 + months) % 12 + 1
    anchor = date(year, month, min(start.day, calendar.monthrange(year, month)[1]))
    years, months = divmod(months, 12)
    return f"{years}y {months}m {(today - anchor).days}d"


def refresh_cards(user, login, out_dir):
    repos = user["repositories"]["nodes"]
    if user["repositories"]["totalCount"] > len(repos):
        raise ValueError("Repository results are truncated; paginate before drawing totals")
    cc = user["contributionsCollection"]
    lang_bytes = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            lang_bytes[name] = lang_bytes.get(name, 0) + edge["size"]
    total_bytes = sum(lang_bytes.values()) or 1
    language_text = ", ".join(
        f"{name} {size / total_bytes:.0%}"
        for name, size in sorted(lang_bytes.items(), key=lambda item: (-item[1], item[0]))[:3]
    ) or "No public language data"
    featured = user["featuredRepository"]
    if featured is None:
        raise ValueError("BuildWithMe-UI was not found; refusing to invent a featured repo")
    today = datetime.now(timezone.utc).date()

    for mode in ("dark", "light"):
        path = os.path.join(out_dir, f"{mode}_mode.svg")
        tree = ET.parse(path)
        root = tree.getroot()
        # Only replace the stats column; keep the existing portrait and frame.
        for element in list(root):
            if element.tag == f"{{{NS}}}text" and element.get("x") == "540":
                root.remove(element)
        colors = (dict(ink="#c9d1d9", title="#58a6ff", label="#ffa657", dim="#484f58")
                  if mode == "dark" else
                  dict(ink="#24292f", title="#0969da", label="#9a6700", dim="#8c959f"))

        def line(y, parts):
            text = ET.SubElement(root, f"{{{NS}}}text", {
                "x": "540", "y": str(y), "font-family": FONT,
                "{http://www.w3.org/XML/1998/namespace}space": "preserve", "font-size": "15",
            })
            for value, color in parts:
                ET.SubElement(text, f"{{{NS}}}tspan", {"fill": colors[color]}).text = str(value)

        def heading(y, title):
            line(y, [(f"─ {title} ", "title"), ("─" * max(0, 56 - len(title)), "dim")])

        def entry(y, label, value):
            line(y, [(f". {label}: ", "label"), (value, "ink")])

        heading(103, f"{login}@github")
        entry(123, "Uptime", account_age(user["createdAt"], today))
        entry(143, "Languages", language_text)
        heading(183, "Contact")
        entry(203, "GitHub", f"github.com/{login}")
        heading(243, "Public repositories & profile")
        entry(263, "Repos / Stars", f"{len(repos)} / {sum(r['stargazerCount'] for r in repos)}")
        entry(283, "Forks / Followers", f"{sum(r['forkCount'] for r in repos)} / {user['followers']['totalCount']}")
        entry(303, "PRs / Issues", f"{user['pullRequests']['totalCount']} / {user['issues']['totalCount']}")
        entry(323, "Top repo", f"{featured['name']} ({featured['stargazerCount']} ★)")
        entry(343, "Top repo selection", "Owner's pick")
        heading(383, "Last 12 Months")
        entry(403, "Contributions / Reviews", f"{cc['contributionCalendar']['totalContributions']} / {cc['totalPullRequestReviewContributions']}")
        entry(423, "Commits / Repos contributed", f"{cc['totalCommitContributions']} / {cc['totalRepositoriesWithContributedCommits']}")
        entry(443, "Private contributions", cc["restrictedContributionsCount"])
        entry(473, "Updated (UTC)", today.isoformat())
        svg = ET.tostring(root, encoding="unicode") + "\n"
        with open(path, encoding="utf-8") as stream:
            old = stream.read()
        if svg != old:
            with open(path, "w", encoding="utf-8") as stream:
                stream.write(svg)
            print(f"updated {mode}_mode.svg")
