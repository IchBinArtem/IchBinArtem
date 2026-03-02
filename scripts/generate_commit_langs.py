#!/usr/bin/env python3
"""Generate language SVG cards from all repos (including private)."""

import os
import math
import requests
from datetime import datetime, timezone, timedelta

TOKEN = os.environ["GITHUB_TOKEN"]
USERNAME = os.environ.get("USERNAME", "IchBinArtem")

HEADERS = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}

LANG_COLORS = {
    "Python": "#3572A5", "PHP": "#4F5D95", "Kotlin": "#A97BFF",
    "TypeScript": "#2b7489", "JavaScript": "#f1e05a", "Rust": "#dea584",
    "Go": "#00ADD8", "Swift": "#F05138", "Java": "#B07219",
    "Shell": "#89e051", "HTML": "#e34c26", "CSS": "#563d7c",
    "C": "#555555", "C++": "#f34b7d", "Pascal": "#E3F171",
    "Pawn": "#dae8f4", "Dart": "#00B4AB",
}
FALLBACK_COLORS = ["#586e75", "#839496", "#93a1a1", "#657b83", "#eee8d5"]
EXCLUDE_LANGS = {"Pascal", "Pawn", "Batchfile", "Makefile", "CMake", "HLSL", "GLSL"}
EXCLUDE_REPOS = {"delphi"}

def get_all_repos():
    repos, page = [], 1
    while True:
        r = requests.get("https://api.github.com/user/repos",
                         headers=HEADERS,
                         params={"per_page": 100, "page": page, "affiliation": "owner"})
        data = r.json()
        if not data or not isinstance(data, list):
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return repos

def get_languages(repo_full_name):
    r = requests.get(f"https://api.github.com/repos/{repo_full_name}/languages", headers=HEADERS)
    return r.json() if r.status_code == 200 and isinstance(r.json(), dict) else {}

def color_for(lang, idx):
    return LANG_COLORS.get(lang, FALLBACK_COLORS[idx % len(FALLBACK_COLORS)])

def generate_svg(title, lang_data):
    top = sorted(lang_data.items(), key=lambda x: x[1], reverse=True)[:5]
    total = sum(v for _, v in top)
    if total == 0:
        return None

    W, H = 340, 200
    cx, cy, r_out, r_in = 250, 110, 60, 35

    slices, angle = [], -math.pi / 2
    for i, (lang, val) in enumerate(top):
        sweep = val / total * 2 * math.pi
        x1 = cx + r_out * math.cos(angle)
        y1 = cy + r_out * math.sin(angle)
        x2 = cx + r_out * math.cos(angle + sweep)
        y2 = cy + r_out * math.sin(angle + sweep)
        xi1 = cx + r_in * math.cos(angle + sweep)
        yi1 = cy + r_in * math.sin(angle + sweep)
        xi2 = cx + r_in * math.cos(angle)
        yi2 = cy + r_in * math.sin(angle)
        large = 1 if sweep > math.pi else 0
        path = (f"M{x1:.2f},{y1:.2f} A{r_out},{r_out},0,{large},1,{x2:.2f},{y2:.2f} "
                f"L{xi1:.2f},{yi1:.2f} A{r_in},{r_in},0,{large},0,{xi2:.2f},{yi2:.2f} Z")
        slices.append((path, color_for(lang, i), lang, val / total * 100))
        angle += sweep

    legend = "".join(
        f'<rect x="30" y="{55 + i*25}" width="14" height="14" fill="{c}"/>'
        f'<text x="50" y="{66 + i*25}" fill="#77909c" font-size="13">{lang} {pct:.1f}%</text>'
        for i, (_, c, lang, pct) in enumerate(slices)
    )
    paths = "".join(
        f'<path d="{p}" fill="{c}" stroke="#0d1117" stroke-width="2"/>'
        for p, c, _, _ in slices
    )

    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">'
            f'<style>* {{ font-family: "Segoe UI", Ubuntu, sans-serif; }}</style>'
            f'<rect x="1" y="1" rx="5" ry="5" width="99%" height="98%" fill="#0d1117" stroke="#2e343b"/>'
            f'<text x="30" y="38" font-size="20" fill="#0366d6">{title}</text>'
            f'{legend}{paths}</svg>')

def save(path, svg):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(svg)
    print(f"Saved: {path}")

def update_readme(repos):
    years = datetime.now(timezone.utc).year - 2012
    total = sum(1 for r in repos if not r.get("fork"))
    rounded = (total // 10) * 10

    readme_path = "README.md"
    with open(readme_path) as f:
        content = f.read()

    import re
    new_line = f"{years} years · {rounded}+ projects · ships ideas as products"
    updated = re.sub(r"\d+ years · \d+\+ projects · ships ideas as products", new_line, content)

    if updated != content:
        with open(readme_path, "w") as f:
            f.write(updated)
        print(f"README updated: {new_line}")
    else:
        print(f"README unchanged: {new_line}")

def main():
    print("Fetching repos...")
    repos = get_all_repos()
    print(f"Found {len(repos)} repos")

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    all_time, last_year = {}, {}

    for repo in repos:
        if repo.get("fork") or repo.get("name") in EXCLUDE_REPOS:
            continue
        langs = get_languages(repo["full_name"])
        pushed = repo.get("pushed_at") or ""
        is_recent = pushed and datetime.fromisoformat(pushed.replace("Z", "+00:00")) >= cutoff

        for lang, b in langs.items():
            if lang in EXCLUDE_LANGS:
                continue
            all_time[lang] = all_time.get(lang, 0) + b
            if is_recent:
                last_year[lang] = last_year.get(lang, 0) + b

    base = "profile-summary-card-output/github_dark"

    update_readme(repos)

    svg = generate_svg("Top Languages · All Time", all_time)
    if svg:
        save(f"{base}/2-most-commit-language.svg", svg)

    svg = generate_svg("Top Languages · Last Month", last_year)
    if svg:
        save(f"{base}/5-last-year-language.svg", svg)
    else:
        print("No last-year data")

if __name__ == "__main__":
    main()
