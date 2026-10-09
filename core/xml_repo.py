"""
CBETAfetch 2.0 - CBETA TEI P5 XML Repository Manager
Handles cloning, pulling, and status queries for https://github.com/cbeta-org/xml-p5
"""

import os
import re
import shutil
import subprocess
import threading
from typing import Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass

from core.progress import render_progress_bar

DEFAULT_XML_P5_REPO = "https://github.com/cbeta-org/xml-p5"


@dataclass
class GitSyncResult:
    success: bool
    action: str  # "clone", "pull", "error", "cancelled"
    message: str
    target_dir: str
    commit_hash: Optional[str] = None


def check_git_installed() -> Tuple[bool, str]:
    """Check whether git binary is available on the system."""
    git_path = shutil.which("git")
    if not git_path:
        return False, "git executable not found in PATH"
    try:
        res = subprocess.run([git_path, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True, res.stdout.strip()
    except Exception:
        return True, f"git binary present at {git_path}"


def get_xml_repo_status(target_dir: str) -> Dict[str, Any]:
    """
    Inspect the local XML repo directory: commit, branch, modified status, XML file count.
    """
    abs_target = os.path.abspath(target_dir)
    if not os.path.isdir(abs_target):
        return {"exists": False, "is_git": False, "target_dir": abs_target}

    dot_git = os.path.join(abs_target, ".git")
    if not os.path.exists(dot_git):
        return {"exists": True, "is_git": False, "target_dir": abs_target}

    status: Dict[str, Any] = {
        "exists": True,
        "is_git": True,
        "target_dir": abs_target,
        "commit": None,
        "branch": None,
        "remote_url": None,
        "xml_file_count": 0
    }

    try:
        # Get current commit
        res = subprocess.run(["git", "-C", abs_target, "rev-parse", "--short", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            status["commit"] = res.stdout.strip()

        # Get branch
        res_branch = subprocess.run(["git", "-C", abs_target, "branch", "--show-current"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res_branch.returncode == 0:
            status["branch"] = res_branch.stdout.strip() or "HEAD (detached)"

        # Get remote URL
        res_remote = subprocess.run(["git", "-C", abs_target, "config", "--get", "remote.origin.url"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res_remote.returncode == 0:
            status["remote_url"] = res_remote.stdout.strip()

        # Count XML files quickly
        xml_count = 0
        for root, _, files in os.walk(abs_target):
            if "/.git" in root or root.endswith(".git"):
                continue
            xml_count += sum(1 for f in files if f.endswith(".xml"))
        status["xml_file_count"] = xml_count

    except Exception as e:
        status["error"] = str(e)

    return status


def clone_or_update_xml_repo(
    repo_url: str = DEFAULT_XML_P5_REPO,
    target_dir: str = "./downloads-xml",
    shallow: bool = True,
    branch: Optional[str] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
    stop_event: Optional[threading.Event] = None
) -> GitSyncResult:
    """
    Clone or update the CBETA TEI P5 XML repository.
    
    If target_dir does not exist or has no .git, performs git clone.
    If target_dir is already a git repo, performs git pull to sync.
    """
    log = progress_callback or (lambda msg: None)
    abs_target = os.path.abspath(target_dir)

    is_installed, git_ver = check_git_installed()
    if not is_installed:
        log(f"Git 未安裝或無法執行: {git_ver}")
        return GitSyncResult(success=False, action="error", message=f"Git not installed: {git_ver}", target_dir=abs_target)

    is_existing_git = os.path.isdir(os.path.join(abs_target, ".git"))

    if is_existing_git:
        action = "pull"
        log(f"偵測到現有 XML Git 倉庫: {abs_target}，正在執行 git pull 同步最新版本...")
        cmd = ["git", "-C", abs_target, "pull", "--progress"]
    else:
        action = "clone"
        os.makedirs(os.path.dirname(abs_target), exist_ok=True)
        log(f"正在克隆 CBETA XML 全藏倉庫: {repo_url} ➔ {abs_target} ...")
        cmd = ["git", "clone", "--progress"]
        if shallow:
            cmd.extend(["--depth", "1"])
            log("啟用淺層 Clone (--depth 1)，大幅節省傳輸頻寬與硬碟空間。")
        if branch:
            cmd.extend(["-b", branch])
        cmd.extend([repo_url, abs_target])

    log(f"執行指令: {' '.join(cmd)}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        output_lines = []
        try:
            while True:
                if stop_event and stop_event.is_set():
                    log("收到任務中斷訊號，正在終止 Git 程序...")
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        try:
                            proc.wait(timeout=2)
                        except Exception:
                            pass
                    return GitSyncResult(success=False, action="cancelled", message="Git sync cancelled by user", target_dir=abs_target)

                try:
                    line = proc.stdout.readline() if proc.stdout else ""
                except Exception:
                    line = ""

                if not line and proc.poll() is not None:
                    break
                if line:
                    cleaned = line.rstrip()
                    output_lines.append(cleaned)
                    m_pct = re.search(r"(\d+)%", cleaned)
                    if m_pct:
                        pct_val = float(m_pct.group(1))
                        log(f"[PROGRESS] {render_progress_bar(pct_val, width=20)} [git] {cleaned}")
                    else:
                        log(f"[git] {cleaned}")

            retcode = proc.poll()
        finally:
            # Ensure stdout pipe file descriptor is closed to avoid OS leak
            if proc.stdout:
                try:
                    proc.stdout.close()
                except Exception:
                    pass
            # Ensure subprocess is reaped if still alive
            if proc.poll() is None:
                try:
                    proc.kill()
                    proc.wait()
                except Exception:
                    pass

        if retcode != 0:
            err_msg = f"Git {action} 執行失敗，回傳碼: {retcode}"
            log(err_msg)
            return GitSyncResult(success=False, action="error", message=err_msg, target_dir=abs_target)

        # Retrieve commit hash
        st = get_xml_repo_status(abs_target)
        commit = st.get("commit")
        succ_msg = f"CBETA XML 全藏庫 {action} 成功完成！目前 Commit: {commit} (共 {st.get('xml_file_count', 0)} 份經文 XML)"
        log(succ_msg)

        return GitSyncResult(
            success=True,
            action=action,
            message=succ_msg,
            target_dir=abs_target,
            commit_hash=commit
        )

    except Exception as e:
        err = f"執行 Git 程序發生異常: {e}"
        log(err)
        return GitSyncResult(success=False, action="error", message=err, target_dir=abs_target)
