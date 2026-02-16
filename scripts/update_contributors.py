from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--limit", type=int, default=200)
    return parser.parse_args()


def next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    parts = [p.strip() for p in link_header.split(",")]
    for part in parts:
        segments = [s.strip() for s in part.split(";")]
        if len(segments) < 2:
            continue
        url = segments[0].strip("<> ")
        rel = segments[1]
        if rel == 'rel="next"':
            return url
    return None


def fetch_contributors(
    repo: str, token: str | None, limit: int
) -> list[dict[str, Any]]:
    contributors: list[dict[str, Any]] = []
    url = f"https://api.github.com/repos/{repo}/contributors?per_page=100&page=1"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "my-agent-team-contributors-bot",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    while url and len(contributors) < limit:
        req = Request(url, headers=headers)
        with urlopen(req) as response:
            payload = json.loads(response.read().decode("utf-8"))
            for item in payload:
                contributors.append(
                    {
                        "login": item.get("login", ""),
                        "html_url": item.get("html_url", ""),
                        "avatar_url": item.get("avatar_url", ""),
                    }
                )
                if len(contributors) >= limit:
                    break
            url = next_link(response.headers.get("Link"))

    return contributors


def avatar_with_size(url: str, size: int) -> str:
    if not url:
        return url
    if "?" in url:
        return f"{url}&s={size}"
    return f"{url}?s={size}"


def render_table(contributors: list[dict[str, Any]], columns: int = 6) -> str:
    if not contributors:
        return "No contributors yet."
    rows = []
    for idx in range(0, len(contributors), columns):
        chunk = contributors[idx : idx + columns]
        cells = []
        for item in chunk:
            login = item["login"]
            html_url = item["html_url"]
            avatar_url = avatar_with_size(item["avatar_url"], 64)
            cells.append(
                f'<td align="center"><a href="{html_url}">'
                f'<img src="{avatar_url}" width="64" height="64" />'
                f"<br />@{login}</a></td>"
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def update_readme(readme_path: Path, contributors_block: str) -> None:
    content = readme_path.read_text(encoding="utf-8")
    pattern = re.compile(r"CONTRIBUTORS_START[\\s\\S]*?CONTRIBUTORS_END")
    replacement = f"CONTRIBUTORS_START\n{contributors_block}\nCONTRIBUTORS_END"
    if not pattern.search(content):
        raise RuntimeError("Contributors markers not found in README.md")
    updated = pattern.sub(replacement, content)
    readme_path.write_text(updated, encoding="utf-8")


def main() -> int:
    args = parse_args()
    if not args.repo:
        print(
            "GITHUB_REPOSITORY is not set and --repo was not provided", file=sys.stderr
        )
        return 2

    readme_path = Path(args.readme)
    if not readme_path.exists():
        print(f"README not found at {readme_path}", file=sys.stderr)
        return 2

    token = os.getenv("GH_TOKEN")
    contributors = fetch_contributors(args.repo, token, args.limit)
    contributors_block = render_table(contributors)
    update_readme(readme_path, contributors_block)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
