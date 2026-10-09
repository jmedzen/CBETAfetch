"""
CBETAfetch 2.0 - FastAPI Application Factory
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server import routes


def create_app() -> FastAPI:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.join(base_dir, "static")

    routes.base_dir = base_dir
    presets_dir = os.path.join(base_dir, "data", "presets")
    routes.preset_manager = routes.PresetManager(storage_dir=presets_dir)

    app = FastAPI(
        title="CBETAfetch 2.0 - Sutra Downloader & Processor",
        description="CBETA 電子佛典多格式批次下載、自動化卷次整理、去重排版與 Markdown 轉換工作台",
        version="2.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    app.include_router(routes.router)

    return app
