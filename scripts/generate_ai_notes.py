# =================================================================
# AI Release Notes Generator Script
# =================================================================
# This script is designed to be called from a GitHub Actions workflow.
# It performs the following steps:
# 1. Determines the git tag range for the release.
# 2. Fetches the commit messages within that range.
# 3. Formats the commits into a clear prompt for an LLM.
# 4. Calls the LLM API to generate a narrative for the release notes.
# 5. Prints the final markdown to standard output.
# =================================================================

import argparse
import os
import subprocess
import sys
import requests

# -----------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------
# This is the system prompt that instructs the LLM on its role,
# tone, and output format. A good system prompt is critical for
# getting high-quality, consistent results.
SYSTEM_PROMPT_TEMPLATE = """
You are an expert technical writer for the open-source project 'my-agent-team'.
Your task is to write the release notes for version `{version}`.

Analyze the user-provided commit messages and generate a high-level, narrative-style summary.
- Group related changes under logical headings (e.g., '🚀 New Features', '🐛 Bug Fixes', '🔧 Maintenance & Refactoring').
- Do NOT simply list the commits. Synthesize the information into a coherent story of what has changed.
- Use markdown for formatting.
- Write in a friendly but professional tone.
- If there are no commits for a certain category, do not include the heading.
- Start with a brief, one-paragraph overview of the release.
"""

# -----------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------


def run_command(command):
    """
    Executes a shell command and returns its output.
    Exits the script if the command fails.
    """
    try:
        # Executes the command, captures stdout, and checks for errors.
        # text=True decodes stdout as UTF-8.
        # check=True raises a CalledProcessError if the command returns a non-zero exit code.
        result = subprocess.run(
            command, check=True, text=True, capture_output=True, shell=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # If the command fails, print the error and exit.
        # This is important for debugging in a CI environment.
        print(f"Error executing command: '{command}'", file=sys.stderr)
        print(f"Stderr: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)


def get_previous_tag(current_tag):
    """
    Finds the tag immediately preceding the current tag in the git history.
    """
    # `git describe --tags --abbrev=0 <tag>~1` is a robust way to find the
    # previous tag. It looks at the commit before the tagged commit.
    command = f"git describe --tags --abbrev=0 {current_tag}~1"
    print(f"🔍 Finding previous tag with command: {command}", file=sys.stderr)
    previous_tag = run_command(command)
    print(f"✅ Found previous tag: {previous_tag}", file=sys.stderr)
    return previous_tag


def get_commit_messages(start_tag, end_tag):
    """
    Gets all commit subjects between two git tags.
    """
    # `git log --pretty=%s` extracts just the subject line of each commit.
    # The range `start_tag..end_tag` includes all commits after start_tag
    # up to and including end_tag.
    command = f"git log --pretty=%s {start_tag}..{end_tag}"
    print(f"📋 Getting commit messages with command: {command}", file=sys.stderr)
    commits = run_command(command)
    print(f"✅ Found {len(commits.splitlines())} commits.", file=sys.stderr)
    return commits


def generate_notes(prompt, api_key, api_url, model_name, version):
    """
    Calls the LLM API to generate the release notes.
    """
    # OpenRouter recommends sending these headers to identify your app.
    # It also helps them with routing and caching.
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/my-agent-team/my-agent-team",  # TODO: Change to your repo URL
        "X-Title": "My Agent Team - AI Release Notes",  # TODO: Change to your project title
    }

    # The payload follows the OpenAI Chat Completions API format.
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT_TEMPLATE.format(version=version),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 1500,
    }

    print(f"🤖 Calling LLM '{model_name}' at '{api_url}'...", file=sys.stderr)

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        release_notes = response.json()["choices"][0]["message"]["content"]
        print("✅ Successfully generated release notes.", file=sys.stderr)
        return release_notes
    except requests.exceptions.RequestException as e:
        print(f"Error calling API: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """
    Main function to orchestrate the script's execution.
    """
    parser = argparse.ArgumentParser(description="Generate AI Release Notes.")
    parser.add_argument("--tag", required=True, help="The new git tag for the release.")
    parser.add_argument("--api-key", required=True, help="API key for the LLM service.")
    parser.add_argument(
        "--api-url",
        default="https://api.openai.com/v1/chat/completions",
        help="The API endpoint for the chat completions service.",
    )
    parser.add_argument(
        "--model", default="gpt-4o", help="The name of the model to use for generation."
    )
    args = parser.parse_args()

    current_tag = args.tag
    previous_tag = get_previous_tag(current_tag)

    commits = get_commit_messages(previous_tag, current_tag)

    if not commits:
        print("No new commits found. Exiting.", file=sys.stderr)
        print(f"# Release {current_tag}\n\nNo new changes in this release.")
        return

    user_prompt = f"Here are the commit messages since tag {previous_tag}:\n\n{commits}"

    ai_notes = generate_notes(
        prompt=user_prompt,
        api_key=args.api_key,
        api_url=args.api_url,
        model_name=args.model,
        version=current_tag,
    )

    print(ai_notes)


if __name__ == "__main__":
    main()
