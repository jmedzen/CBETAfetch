"""
Pytest configuration and common fixtures for CBETAfetch 2.0.
"""

import os
import sys
import shutil
import tempfile
import pytest
from starlette.testclient import TestClient

# Ensure project root is in python path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from server.app import create_app
from server import routes
from core.job_engine import JobEngine


@pytest.fixture
def temp_dir():
    """Provides a temporary workspace directory that is cleaned up after test."""
    d = tempfile.mkdtemp(prefix="cbeta_test_")
    yield d
    if os.path.exists(d):
        shutil.rmtree(d)


@pytest.fixture
def client(temp_dir):
    """Provides a FastAPI test client with isolated base_dir and job_engine."""
    test_app = create_app()
    routes.base_dir = temp_dir
    routes.job_engine = JobEngine()
    
    # Create required subdirs in temp_dir
    os.makedirs(os.path.join(temp_dir, "downloads"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "complete"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "templates"), exist_ok=True)
    
    # Copy index.html to temp template dir for test
    src_index = os.path.join(base_dir, "templates", "index.html")
    if os.path.exists(src_index):
        shutil.copy(src_index, os.path.join(temp_dir, "templates", "index.html"))

    with TestClient(test_app) as c:
        yield c
