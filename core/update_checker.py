"""
CBETAfetch 2.0 - Remote Update Checker
Fetches the last modified time and metadata for:
1. Complete text pack ZIP URL (via HTTP HEAD request)
2. CBETA TEI P5 XML Git repository (via GitHub API / git ls-remote / local git log)
"""

import os
import re
import ssl
import json
import urllib.request
import urllib.error
import subprocess
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, Any, Optional

DEFAULT_ZIP_URL = "https://cbdata.dila.edu.tw/stable/download/cbeta-text.zip"
DEFAULT_GIT_REPO = "https://github.com/cbeta-org/xml-p5"


def format_iso_datetime(dt: datetime) -> str:
    """Format datetime object into localized ISO-like string YYYY-MM-DD HH:MM:SS."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_zip_remote_metadata(url: str = DEFAULT_ZIP_URL, timeout: int = 6) -> Dict[str, Any]:
    """
    Query HTTP HEAD for the ZIP file to extract Last-Modified and Content-Length.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "CBETAfetch/2.0 (Buddhist Digital Humanities Tool)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            last_mod_header = response.getheader("Last-Modified")
            content_length = response.getheader("Content-Length")
            etag = response.getheader("ETag")

            last_mod_str = "未提供"
            last_mod_iso = None
            if last_mod_header:
                try:
                    dt = parsedate_to_datetime(last_mod_header)
                    last_mod_str = format_iso_datetime(dt)
                    last_mod_iso = dt.isoformat()
                except Exception:
                    last_mod_str = last_mod_header

            size_bytes = int(content_length) if content_length and content_length.isdigit() else 0
            size_mb = round(size_bytes / (1024 * 1024), 1) if size_bytes else None

            return {
                "success": True,
                "url": url,
                "last_modified": last_mod_str,
                "last_modified_iso": last_mod_iso,
                "size_bytes": size_bytes,
                "size_mb": size_mb,
                "etag": etag.strip('"') if etag else None
            }

    except Exception as e:
        return {
            "success": False,
            "url": url,
            "error": str(e),
            "last_modified": "查詢失敗",
            "size_mb": None
        }


def get_git_remote_metadata(repo_url: str = DEFAULT_GIT_REPO, local_dir: Optional[str] = None, timeout: int = 6) -> Dict[str, Any]:
    """
    Query the latest commit date, author, and commit message for a Git repository.
    Supports GitHub API, local Git clone inspection, or fallback git command.
    """
    # 1. If it's a GitHub repository, query GitHub Commits API
    github_match = re.search(r"github\.com[/:]([\w\-]+)/([\w\-]+)(?:\.git)?", repo_url)
    if github_match:
        owner, repo = github_match.group(1), github_match.group(2)
        api_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "CBETAfetch/2.0",
                "Accept": "application/vnd.github.v3+json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                data = json.loads(response.read().decode("utf-8"))
                if isinstance(data, list) and len(data) > 0:
                    latest = data[0]
                    sha = latest.get("sha", "")[:7]
                    commit_obj = latest.get("commit", {})
                    author_obj = commit_obj.get("committer") or commit_obj.get("author") or {}
                    raw_date = author_obj.get("date")

                    date_str = raw_date
                    if raw_date:
                        try:
                            # 2026-09-05T18:53:36Z
                            clean_d = raw_date.replace("Z", "+00:00")
                            dt = datetime.fromisoformat(clean_d)
                            date_str = format_iso_datetime(dt)
                        except Exception:
                            pass

                    return {
                        "success": True,
                        "source": "github_api",
                        "repo_url": repo_url,
                        "last_modified": date_str,
                        "commit_hash": sha,
                        "commit_message": commit_obj.get("message", "").split("\n")[0],
                        "author": author_obj.get("name", "")
                    }
        except Exception:
            pass  # Fallback to local or git command

    # 2. If local clone directory exists, check git log
    if local_dir and os.path.isdir(os.path.join(local_dir, ".git")):
        try:
            res = subprocess.run(
                ["git", "-C", local_dir, "log", "-1", "--format=%cI%n%h%n%s%n%an"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout
            )
            if res.returncode == 0:
                lines = res.stdout.strip().splitlines()
                if len(lines) >= 4:
                    raw_date, sha, msg, author = lines[0], lines[1], lines[2], lines[3]
                    try:
                        dt = datetime.fromisoformat(raw_date)
                        date_str = format_iso_datetime(dt)
                    except Exception:
                        date_str = raw_date
                    return {
                        "success": True,
                        "source": "local_git",
                        "repo_url": repo_url,
                        "last_modified": date_str,
                        "commit_hash": sha,
                        "commit_message": msg,
                        "author": author
                    }
        except Exception:
            pass

    return {
        "success": False,
        "repo_url": repo_url,
        "last_modified": "無法取得最新提交時間",
        "commit_hash": None
    }


def get_all_remote_updates(zip_url: str = DEFAULT_ZIP_URL, git_url: str = DEFAULT_GIT_REPO, local_xml_dir: Optional[str] = None) -> Dict[str, Any]:
    """Fetch update status for both ZIP and Git repo."""
    zip_meta = get_zip_remote_metadata(zip_url)
    git_meta = get_git_remote_metadata(git_url, local_dir=local_xml_dir)
    return {
        "zip_pack": zip_meta,
        "git_repo": git_meta
    }
