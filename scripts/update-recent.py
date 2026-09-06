#!/usr/bin/env python3
"""Refresh the RECENT block in README.md from the GitHub API.

Shows my latest personal repos and my latest external PRs (open or merged),
excluding forks and anything under the accel-com org. Run by a scheduled
GitHub Action; safe to run locally with the `gh` CLI authenticated.
"""

import datetime
import json
import pathlib
import re
import subprocess

USER = "rachittshah"
PROFILE_REPO = f"{USER}/{USER}"
N_REPOS = 3
N_PRS = 2
DESC_MAX = 46


def gh(*args: str) -> str:
  return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def clip(s: str) -> str:
  s = " ".join((s or "").split())
  if len(s) <= DESC_MAX:
    return s
  return s[:DESC_MAX].rsplit(" ", 1)[0] + "…"


def rel(iso: str) -> str:
  d = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
  days = (datetime.datetime.now(datetime.timezone.utc) - d).days
  if days <= 0:
    return "today"
  if days < 30:
    return f"{days}d ago"
  if days < 365:
    return f"{days // 30}mo ago"
  return f"{days // 365}y ago"


def item(label: str, url: str, desc: str, meta: str) -> str:
  head = f"- [{label}]({url})" + (f" — {clip(desc)}" if desc else "")
  return f"{head} <br><sub><i>{meta}</i></sub>"


def latest_repos() -> list[str]:
  repos = json.loads(gh("api", f"users/{USER}/repos?per_page=100&sort=pushed&type=owner"))
  out = []
  for r in repos:
    if r["fork"] or r["archived"] or r["full_name"] == PROFILE_REPO:
      continue
    bits = [r["language"] or "—"]
    if r["stargazers_count"]:
      bits.append(f"{r['stargazers_count']}★")
    bits.append(f"updated {rel(r['pushed_at'])}")
    out.append(item(r["name"], r["html_url"], r["description"], " · ".join(bits)))
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
    state = "merged" if merged else it["state"]
    meta = f"{state} · {rel(it['created_at'])}"
    out.append(item(f"{owner_repo}#{it['number']}", it["html_url"], it["title"], meta))
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
