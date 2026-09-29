"""Post the issues in issues.md to a GitHub repo (and optionally a Project) via the gh CLI.

Each issue is a section starting with ``## [HL-xx] Title`` followed by a
``<!-- labels: a, b -->`` line. Sections are created in file order; afterwards every
``HL-xx`` reference in the bodies is rewritten to the created ``#N`` issue number.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HEADER = re.compile(r"^## \[(HL-[A-Z]?\d+)\] (.+)$", re.MULTILINE)
LABELS = re.compile(r"^<!-- labels: (.+?) -->\s*$", re.MULTILINE)
REF = re.compile(r"\bHL-[A-Z]?\d+\b")
LABEL_COLORS = {"type:": "1d76db", "domain:": "0e8a16", "area:": "5319e7", "priority:": "d93f0b", "source:": "fbca04"}


def parse(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    matches = list(HEADER.finditer(text))
    issues = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else text.find("\n## Posting these issues")
        chunk = text[m.end() : end if end != -1 else len(text)]
        label_match = LABELS.search(chunk)
        labels = [s.strip() for s in label_match.group(1).split(",")] if label_match else []
        body = LABELS.sub("", chunk, count=1).strip().removesuffix("---").strip()
        issues.append({"key": m.group(1), "title": m.group(2).strip(), "labels": labels, "body": body})
    return issues


def gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        sys.exit(f"gh {' '.join(args[:3])} failed:\n{result.stderr}")
    return result.stdout.strip()


def ensure_labels(repo: str, labels: set[str]) -> None:
    existing = {item["name"] for item in json.loads(gh("label", "list", "--repo", repo, "--limit", "500", "--json", "name"))}
    for label in sorted(labels - existing):
        color = next((c for prefix, c in LABEL_COLORS.items() if label.startswith(prefix)), "ededed")
        gh("label", "create", label, "--repo", repo, "--color", color)
        print(f"created label {label}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--file", default=str(Path(__file__).with_name("issues.md")))
    parser.add_argument("--project", type=int, help="GitHub Project number to add issues to")
    parser.add_argument("--project-owner", help="user or org that owns the Project")
    parser.add_argument("--only", help="comma-separated keys, e.g. HL-01,HL-05")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--update", action="store_true", help="edit existing issues (matched by title) instead of creating")
    args = parser.parse_args()
    if args.project and not args.project_owner:
        parser.error("--project requires --project-owner")

    issues = parse(Path(args.file))
    if args.only:
        wanted = {k.strip() for k in args.only.split(",")}
        issues = [i for i in issues if i["key"] in wanted]

    if args.dry_run:
        for issue in issues:
            print(f"{issue['key']}: {issue['title']}  [{', '.join(issue['labels'])}]  ({len(issue['body'])} chars)")
        print(f"{len(issues)} issues parsed; nothing posted.")
        return

    ensure_labels(args.repo, {label for issue in issues for label in issue["labels"]})

    numbers: dict[str, str] = {}
    urls: dict[str, str] = {}
    if args.update:
        existing = json.loads(gh("issue", "list", "--repo", args.repo, "--state", "all", "--limit", "500", "--json", "number,title,url,labels"))
        by_title = {item["title"]: item for item in existing}
        for issue in issues:
            item = by_title.get(issue["title"])
            if item is None:
                sys.exit(f"{issue['key']}: no existing issue titled {issue['title']!r}; create it first")
            urls[issue["key"]] = item["url"]
            numbers[issue["key"]] = f"#{item['number']}"
    else:
        for issue in issues:
            cmd = ["issue", "create", "--repo", args.repo, "--title", issue["title"], "--body", issue["body"]]
            for label in issue["labels"]:
                cmd += ["--label", label]
            url = gh(*cmd)
            urls[issue["key"]] = url
            numbers[issue["key"]] = "#" + url.rstrip("/").rsplit("/", 1)[-1]
            print(f"{issue['key']} -> {url}")
            if args.project:
                gh("project", "item-add", str(args.project), "--owner", args.project_owner, "--url", url)

    for issue in issues:
        body = REF.sub(lambda m: numbers.get(m.group(0), m.group(0)), issue["body"])
        if args.update:
            cmd = ["issue", "edit", urls[issue["key"]], "--body", body]
            current = {label["name"] for label in by_title[issue["title"]]["labels"]}
            for label in set(issue["labels"]) - current:
                cmd += ["--add-label", label]
            for label in current - set(issue["labels"]):
                cmd += ["--remove-label", label]
            gh(*cmd)
            print(f"updated {issue['key']} {numbers[issue['key']]}")
        elif body != issue["body"]:
            gh("issue", "edit", urls[issue["key"]], "--body", body)
            print(f"linked references in {issue['key']}")


if __name__ == "__main__":
    main()
