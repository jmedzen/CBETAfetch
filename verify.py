#!/usr/bin/env python3
"""
CBETAfetch 2.0 - Comprehensive Self-Test & Diagnostic Runner (全系統自我檢測驗證程式)
用法：
    python verify.py
    python verify.py --pytest
"""

import sys
import os
import subprocess

# Ensure project root is in sys.path
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from core.diagnostics import SystemDiagnostics
from core.job_engine import JobEngine


def print_banner():
    print(r"""
========================================================================
   ____ ____  _____ _____  _      __      _       _     ____  
  / ___| __ )| ____|_   _|/ \    / _| ___| |_ ___| |__ |___ \ 
 | |   |  _ \|  _|   | | / _ \  | |_ / _ \ __/ __| '_ \  __) |
 | |___| |_) | |___  | |/ ___ \ |  _|  __/ || (__| | | |/ __/ 
  \____|____/|_____| |_/_/   \_\|_|  \___|\__\___|_| |_|_____|
========================================================================
 ☸ CBETA Sutra Downloader & Processor 2.0 · 全系統自我功能檢測與健康診斷
------------------------------------------------------------------------""")


def main():
    print_banner()

    run_pytest_flag = "--pytest" in sys.argv or "-p" in sys.argv

    je = JobEngine()
    print("🚀 正在啟動全子系統檢測，請稍候...\n")
    report = SystemDiagnostics.run_all_checks(base_dir=base_dir, job_engine=je)

    # Print results table
    print(f"{'狀態':<6} | {'類別':<10} | {'檢測項目':<38} | {'耗時':<8}")
    print("-" * 74)

    status_icons = {
        "passed": "\033[92m✔ 通過\033[0m",
        "warning": "\033[93m▲ 警示\033[0m",
        "failed": "\033[91m✖ 失敗\033[0m"
    }

    for res in report.results:
        icon = status_icons.get(res.status, res.status)
        ms = f"{res.duration_ms}ms"
        print(f"{icon:<15} | {res.category:<10} | {res.name:<36} | {ms:<8}")
        if res.status != "passed":
            print(f"      └─ \033[90m{res.message}\033[0m")

    print("-" * 74)
    overall_color = "\033[92m" if report.failed_count == 0 else "\033[91m"
    print(f"診斷時間: {report.timestamp} | 總耗時: {report.total_duration_ms}ms")
    print(f"檢測結果: {overall_color}通過: {report.passed_count}/{report.total_tests} 項\033[0m | 警示: {report.warning_count} | 失敗: {report.failed_count}")
    print("=" * 74)

    if run_pytest_flag:
        print("\n🧪 正在執行 Pytest 自動化測試單元...")
        pytest_cmd = [sys.executable, "-m", "pytest", "tests", "-v"]
        p_res = subprocess.run(pytest_cmd, cwd=base_dir)
        if p_res.returncode != 0:
            print("\n❌ Pytest 測試發現未通過項目！")
            sys.exit(p_res.returncode)

    if report.failed_count > 0:
        print("\n❌ 自我功能檢測發現致命錯誤，請檢視上方錯誤日誌！")
        sys.exit(1)
    else:
        print("\n✨ 所有自我功能檢測項目均已圓滿完成！系統準備就緒。")
        sys.exit(0)


if __name__ == "__main__":
    main()
