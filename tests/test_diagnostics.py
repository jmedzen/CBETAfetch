"""
Unit tests for core.diagnostics module.
"""

import os
import pytest
from core.diagnostics import SystemDiagnostics


def test_python_environment_check():
    res = SystemDiagnostics.check_python_environment()
    assert res.status == "passed"


def test_workspace_directories_check(temp_dir):
    res = SystemDiagnostics.check_workspace_directories(temp_dir)
    assert res.status == "passed"


def test_id_parser_check():
    res = SystemDiagnostics.check_id_parser_engine()
    assert res.status == "passed"


def test_two_letter_canons_check():
    res = SystemDiagnostics.check_two_letter_canons()
    assert res.status == "passed"


def test_url_builder_check():
    res = SystemDiagnostics.check_url_builder_formats()
    assert res.status == "passed"


def test_headings_engine_check():
    res = SystemDiagnostics.check_headings_engine()
    assert res.status == "passed"


def test_heading_deduplication_check():
    res = SystemDiagnostics.check_heading_deduplication()
    assert res.status == "passed"


def test_converter_sanitization_check():
    res = SystemDiagnostics.check_converter_sanitization()
    assert res.status == "passed"


def test_processor_toc_ordering_check():
    res = SystemDiagnostics.check_processor_toc_ordering()
    assert res.status == "passed"


def test_processor_metadata_check():
    res = SystemDiagnostics.check_processor_metadata_extraction()
    assert res.status == "passed"


def test_job_lifecycle_check():
    res = SystemDiagnostics.check_job_lifecycle(None)
    assert res.status == "passed"


def test_network_connectivity_check():
    res = SystemDiagnostics.check_network_connectivity()
    # In sandbox or offline, warning or passed are valid
    assert res.status in ("passed", "warning")


def test_run_all_checks(temp_dir):
    report = SystemDiagnostics.run_all_checks(temp_dir)
    assert report.total_tests == 13
    assert report.failed_count == 0
    assert report.passed_count >= 12
