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
        rel = segments[1].replace('"', "")
        if "rel=next" in rel:
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
        "User-Agent": f"contributor-bot-{repo}",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    print(f"🔍 Fetching contributors for {repo}...")

    while url and len(contributors) < limit:
        req = Request(url, headers=headers)
        try:
            with urlopen(req) as response:
                payload = json.loads(response.read().decode("utf-8"))
                for item in payload:
                    # Filter out bots to keep the list clean
                    if item.get("type") == "Bot":
                        continue
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
        except Exception as e:
            print(f"❌ Error fetching contributors: {e}", file=sys.stderr)
            break

    return contributors


def render_table(contributors: list[dict[str, Any]], columns: int = 6) -> str:
    if not contributors:
        return "No contributors yet."
    rows = []
    for idx in range(0, len(contributors), columns):
        chunk = contributors[idx : idx + columns]
        cells = []
        for item in chunk:
            # GitHub avatars usually support the 's' parameter for sizing
            avatar_url = (
                f"{item['avatar_url']}&s=64"
                if "?" in item["avatar_url"]
                else f"{item['avatar_url']}?s=64"
            )
            cells.append(
                f'<td align="center"><a href="{item["html_url"]}">'
                f'<img src="{avatar_url}" width="64" height="64" style="border-radius:50%" />'
                f"<br /><b>@{item['login']}</b></a></td>"
            )
        rows.append("  <tr>" + "".join(cells) + "</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def update_readme(readme_path: Path, contributors_block: str) -> None:
    content = readme_path.read_text(encoding="utf-8")

    # Matches your exact README markers: CONTRIBUTORS_START ... CONTRIBUTORS_END
    pattern = re.compile(r"CONTRIBUTORS_START[\s\S]*?CONTRIBUTORS_END")
    replacement = f"CONTRIBUTORS_START\n{contributors_block}\nCONTRIBUTORS_END"

    if not pattern.search(content):
        print("❌ ERROR: Could not find markers in README.md")
        print(
            "Ensure your README contains exactly: CONTRIBUTORS_START and CONTRIBUTORS_END"
        )
        sys.exit(1)

    updated = pattern.sub(replacement, content)
    readme_path.write_text(updated, encoding="utf-8")
    print("🚀 README.md updated successfully with new contributor table.")


def main() -> int:
    args = parse_args()
    if not args.repo:
        print("❌ Error: GITHUB_REPOSITORY is not set.", file=sys.stderr)
        return 1

    readme_path = Path(args.readme)
    if not readme_path.exists():
        print(f"❌ Error: {readme_path} not found.", file=sys.stderr)
        return 1

    token = os.getenv("GH_TOKEN")
    contributors = fetch_contributors(args.repo, token, args.limit)

    # If we find 0 contributors (unlikely if you've committed), we don't want to break the README
    if contributors:
        block = render_table(contributors)
        update_readme(readme_path, block)
    else:
        print("ℹ️ No contributors found. Skipping update.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
