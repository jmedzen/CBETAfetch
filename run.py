#!/usr/bin/env python3
"""
CBETAfetch 2.0 - Sutra Downloader & Processor 2.0 Entry Point
"""

import sys
import os
import argparse
import threading
import webbrowser

base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

import uvicorn
from server.app import create_app
from core.diagnostics import SystemDiagnostics


def main():
    parser = argparse.ArgumentParser(description="CBETAfetch 2.0 - Sutra Downloader & Processor")
    parser.add_argument("--port", type=int, default=int(os.environ.get("CBETA_PORT", 10067)), help="Server port (default: 10067)")
    parser.add_argument("--host", type=str, default=os.environ.get("CBETA_HOST", "127.0.0.1"), help="Server host (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open browser")
    parser.add_argument("--self-test", action="store_true", help="Run system diagnostics and exit")

    args = parser.parse_args()

    if args.self_test:
        print("🚀 Running CBETAfetch 2.0 Diagnostics...")
        report = SystemDiagnostics.run_all_checks(base_dir)
        print(f"Results: {report.passed_count}/{report.total_tests} passed, {report.warning_count} warnings, {report.failed_count} failed in {report.total_duration_ms}ms")
        sys.exit(1 if report.failed_count > 0 else 0)

    port = args.port
    host = args.host

    print(rf"""
========================================================================
   ____ ____  _____ _____  _      __      _       _     ____  
  / ___| __ )| ____|_   _|/ \    / _| ___| |_ ___| |__ |___ \ 
 | |   |  _ \|  _|   | | / _ \  | |_ / _ \ __/ __| '_ \  __) |
 | |___| |_) | |___  | |/ ___ \ |  _|  __/ || (__| | | |/ __/ 
  \____|____/|_____| |_/_/   \_\|_|  \___|\__\___|_| |_|_____|
========================================================================
 ☸ CBETA Sutra Downloader & Processor 2.0
------------------------------------------------------------------------
 🌐 Web UI 介面:  http://{host}:{port}
 📄 API Swagger: http://{host}:{port}/docs
 🧪 系統自檢:    http://{host}:{port} (前往「系統自檢」分頁)
 📁 專案根目錄:  {base_dir}
========================================================================
""")

    if not args.no_browser and host in ("127.0.0.1", "localhost"):
        def open_browser():
            import time
            time.sleep(1.2)
            webbrowser.open(f"http://{host}:{port}")
        threading.Thread(target=open_browser, daemon=True).start()

    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
