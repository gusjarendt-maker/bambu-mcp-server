"""Tests for mesh tools."""

import tempfile
from pathlib import Path

import numpy as np
import trimesh

from bambu_mcp.tools.mesh import analyze, repair, scale, rotate, mirror, calculate_scale


def _make_test_stl(tmp_dir: str) -> str:
    """Create a simple test STL (a box)."""
    mesh = trimesh.creation.box(extents=[50, 30, 100])
    path = str(Path(tmp_dir) / "test_box.stl")
    mesh.export(path)
    return path


def test_analyze():
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_test_stl(tmp)
        result = analyze(path)
        assert result["vertices"] > 0
        assert result["faces"] > 0
        assert result["watertight"] is True
        assert result["non_manifold_edges"] == 0
        assert abs(result["extents_mm"]["x"] - 50) < 1
        assert abs(result["extents_mm"]["z"] - 100) < 1


def test_repair():
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_test_stl(tmp)
        result = repair(path)
        assert result["after"]["watertight"] is True
        assert Path(result["output"]).exists()


def test_scale_factor():
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_test_stl(tmp)
        result = scale(path, factor=0.5)
        assert abs(result["scaled_mm"]["x"] - 25) < 1
        assert abs(result["scaled_mm"]["z"] - 50) < 1
        assert Path(result["output"]).exists()


def test_scale_target():
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_test_stl(tmp)
        result = scale(path, target_mm={"z": 50})
        assert abs(result["scaled_mm"]["z"] - 50) < 1
        assert Path(result["output"]).exists()


def test_rotate():
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_test_stl(tmp)
        result = rotate(path, axis="x", angle_degrees=90)
        # After 90° rotation on X, Y and Z swap
        assert abs(result["extents_mm"]["y"] - 100) < 1
        assert abs(result["extents_mm"]["z"] - 30) < 1
        assert Path(result["output"]).exists()


def test_mirror():
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_test_stl(tmp)
        result = mirror(path, axis="x")
        assert abs(result["extents_mm"]["x"] - 50) < 1
        assert Path(result["output"]).exists()


def test_calculate_scale():
    result = calculate_scale(
        model_extents_mm={"x": 96.1, "y": 63.1, "z": 206.7},
        target_circumference_mm=170,
        target_length_mm=100,
        clearance_pct=5.0,
    )
    assert "final_scale_pct" in result
    assert 55 < result["final_scale_pct"] < 65
    assert result["clearance_pct"] == 5.0
