"""Tests for slicer tools."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import trimesh

from bambu_mcp.tools.slicer import (
    detect,
    list_profiles,
    slice_model,
    export_3mf,
    model_info,
    _find_bambu_cli,
    _find_profile_dirs,
)


def _make_test_stl(tmp_dir: str) -> str:
    """Create a simple test STL (a box)."""
    mesh = trimesh.creation.box(extents=[50, 30, 100])
    path = str(Path(tmp_dir) / "test_box.stl")
    mesh.export(path)
    return path


# ── Detection Tests ────────────────────────────────────────────────────


def test_detect_returns_dict():
    result = detect()
    assert isinstance(result, dict)
    assert "installed" in result
    assert "cli_path" in result
    assert "platform" in result
    assert "profile_directories" in result


def test_detect_finds_bambu_if_installed():
    """If Bambu Studio is installed, detect should find it."""
    result = detect()
    if result["installed"]:
        assert result["cli_path"] is not None
        assert Path(result["cli_path"]).exists()


# ── Profile Listing Tests ─────────────────────────────────────────────


def test_list_profiles_returns_dict():
    result = list_profiles()
    assert isinstance(result, dict)
    if "error" not in result:
        assert "profiles" in result
        assert "summary" in result
        assert "total" in result


def test_list_profiles_invalid_type():
    result = list_profiles(profile_type="invalid")
    assert "error" in result


def test_list_profiles_machine_only():
    result = list_profiles(profile_type="machine")
    if "error" not in result:
        assert "machine" in result["profiles"]
        assert "filament" not in result["profiles"]
        assert "process" not in result["profiles"]


def test_list_profiles_all_vendors():
    result = list_profiles(vendor="all")
    if "error" not in result:
        assert result["total"] >= 0


# ── Slice Tests (mocked CLI) ──────────────────────────────────────────


def test_slice_file_not_found():
    result = slice_model("/nonexistent/file.stl")
    assert "error" in result


def test_slice_with_mock_cli():
    with tempfile.TemporaryDirectory() as tmp:
        stl_path = _make_test_stl(tmp)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Slicing done."
        mock_result.stderr = ""

        with patch("bambu_mcp.tools.slicer._find_bambu_cli", return_value="/fake/cli"), \
             patch("subprocess.run", return_value=mock_result):
            result = slice_model(stl_path, output_dir=tmp)
            assert result["success"] is True
            assert result["input"] == stl_path
            assert result["output_dir"] == tmp


def test_slice_no_bambu_installed():
    with tempfile.TemporaryDirectory() as tmp:
        stl_path = _make_test_stl(tmp)

        with patch("bambu_mcp.tools.slicer._find_bambu_cli", return_value=None):
            result = slice_model(stl_path)
            assert "error" in result


# ── Export 3MF Tests (mocked CLI) ─────────────────────────────────────


def test_export_3mf_file_not_found():
    result = export_3mf("/nonexistent/file.stl")
    assert "error" in result


def test_export_3mf_with_mock_cli():
    with tempfile.TemporaryDirectory() as tmp:
        stl_path = _make_test_stl(tmp)
        output_3mf = str(Path(tmp) / "test_box.3mf")

        # Create a fake 3mf output file
        Path(output_3mf).touch()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Export done."
        mock_result.stderr = ""

        with patch("bambu_mcp.tools.slicer._find_bambu_cli", return_value="/fake/cli"), \
             patch("subprocess.run", return_value=mock_result):
            result = export_3mf(stl_path, output_path=output_3mf)
            assert result["success"] is True
            assert result["output"] == output_3mf


# ── Model Info Tests (mocked CLI) ─────────────────────────────────────


def test_model_info_file_not_found():
    result = model_info("/nonexistent/file.stl")
    assert "error" in result


def test_model_info_with_mock_cli():
    with tempfile.TemporaryDirectory() as tmp:
        stl_path = _make_test_stl(tmp)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Model: test_box.stl\nVertices: 8\nFaces: 12"
        mock_result.stderr = ""

        with patch("bambu_mcp.tools.slicer._find_bambu_cli", return_value="/fake/cli"), \
             patch("subprocess.run", return_value=mock_result):
            result = model_info(stl_path)
            assert result["success"] is True
            assert "info" in result
