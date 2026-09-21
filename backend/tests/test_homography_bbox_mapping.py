"""Legacy alignment/homography test — superseded by hybrid VLM pipeline.

This test was written for the old ORB/RANSAC alignment + compare_single_page pipeline,
both of which have been removed. Replaced with a stub that always passes to avoid
CI failures from a deleted module import.

For new pipeline tests, see test_hybrid_pipeline.py.
"""
import pytest


def test_whole_image_comparison_pipeline_stub():
    """Stub: original alignment/compare_single_page test superseded by hybrid pipeline."""
    # The old pipeline (align.py, compare_single_page) has been removed.
    # This test is intentionally a no-op stub to prevent import errors.
    # See test_hybrid_pipeline.py for new pipeline tests.
    assert True, "Stub always passes"
