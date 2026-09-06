#!/usr/bin/env python3
"""Refresh the RECENT block in README.md from the GitHub API.

Shows my latest personal repos and my latest external PRs (open or merged),
excluding forks and anything under the accel-com org. Run by a scheduled
GitHub Action; safe to run locally with the `gh` CLI authenticated.
"""

import json
import pathlib
import re
import subprocess

USER = "rachittshah"
PROFILE_REPO = f"{USER}/{USER}"
N_REPOS = 3
N_PRS = 2
DESC_MAX = 72


def gh(*args: str) -> str:
  return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def clip(s: str) -> str:
  s = " ".join((s or "").split())
  return s if len(s) <= DESC_MAX else s[: DESC_MAX - 1].rstrip() + "…"


def line(label: str, url: str, desc: str) -> str:
  return f"- [{label}]({url})" + (f" — {clip(desc)}" if desc else "")


def latest_repos() -> list[str]:
  repos = json.loads(gh("api", f"users/{USER}/repos?per_page=100&sort=pushed&type=owner"))
  out = []
  for r in repos:
    if r["fork"] or r["archived"] or r["full_name"] == PROFILE_REPO:
      continue
    out.append(line(r["name"], r["html_url"], r["description"]))
    if len(out) >= N_REPOS:
      break
  return out


def latest_prs() -> list[str]:
  q = f"author:{USER}+type:pr+-user:{USER}+-user:accel-com"
  res = json.loads(gh("api", f"search/issues?q={q}&sort=created&order=desc&per_page=30"))
  out = []
  for it in res["items"]:
    merged = (it.get("pull_request") or {}).get("merged_at")
    if it["state"] == "closed" and not merged:
      continue  # skip closed-unmerged
    owner_repo = "/".join(it["repository_url"].split("/")[-2:])
    out.append(line(f"{owner_repo}#{it['number']}", it["html_url"], it["title"]))
    if len(out) >= N_PRS:
      break
  return out


def main() -> None:
  block = "\n".join(latest_repos() + latest_prs())
  path = pathlib.Path("README.md")
  text = path.read_text()
  replacement = f"<!-- RECENT:START -->\n{block}\n<!-- RECENT:END -->"
  new = re.sub(
    r"<!-- RECENT:START -->.*?<!-- RECENT:END -->",
    lambda _m: replacement,
    text,
    flags=re.S,
  )
  path.write_text(new)


if __name__ == "__main__":
  main()
