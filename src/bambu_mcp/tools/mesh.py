"""Mesh tools — analyze, repair, scale, rotate, mirror, convert."""

from __future__ import annotations

import math
from pathlib import Path
from collections import defaultdict

import numpy as np
import trimesh
import pymeshfix


def _count_non_manifold(mesh: trimesh.Trimesh) -> int:
    """Count non-manifold edges in a mesh."""
    edge_to_faces: dict[tuple, list[int]] = defaultdict(list)
    for fi, face in enumerate(mesh.faces):
        vs = tuple(sorted(face))
        for i in range(3):
            for j in range(i + 1, 3):
                edge_to_faces[(vs[i], vs[j])].append(fi)
    return sum(1 for v in edge_to_faces.values() if len(v) > 2)


def _count_boundary(mesh: trimesh.Trimesh) -> int:
    """Count boundary (open) edges in a mesh."""
    edge_to_faces: dict[tuple, list[int]] = defaultdict(list)
    for fi, face in enumerate(mesh.faces):
        vs = tuple(sorted(face))
        for i in range(3):
            for j in range(i + 1, 3):
                edge_to_faces[(vs[i], vs[j])].append(fi)
    return sum(1 for v in edge_to_faces.values() if len(v) == 1)


def analyze(file_path: str) -> dict:
    """Analyze an STL/OBJ/3MF file and return mesh metrics."""
    mesh = trimesh.load(file_path)
    bounds = mesh.bounds
    extents = mesh.extents

    # Detect if units are in meters (values < 1.0 in all axes)
    likely_meters = all(e < 1.0 for e in extents)
    scale_note = ""
    display_extents = extents
    if likely_meters:
        display_extents = extents * 1000
        scale_note = " (file appears to be in meters, showing mm)"

    return {
        "file": file_path,
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "extents_mm": {
            "x": round(float(display_extents[0]), 2),
            "y": round(float(display_extents[1]), 2),
            "z": round(float(display_extents[2]), 2),
        },
        "volume_mm3": round(float(mesh.volume * (1e9 if likely_meters else 1)), 2),
        "watertight": mesh.is_watertight,
        "non_manifold_edges": _count_non_manifold(mesh),
        "boundary_edges": _count_boundary(mesh),
        "unit_note": scale_note.strip(),
    }


def repair(file_path: str, output_path: str | None = None) -> dict:
    """Repair non-manifold edges, holes, and normals using pymeshfix."""
    mesh = trimesh.load(file_path)
    original_stats = {
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "watertight": mesh.is_watertight,
        "non_manifold_edges": _count_non_manifold(mesh),
    }

    meshfix = pymeshfix.MeshFix(mesh.vertices, mesh.faces)
    meshfix.repair()

    mesh_fixed = trimesh.Trimesh(vertices=meshfix.points, faces=meshfix.faces)

    if output_path is None:
        p = Path(file_path)
        output_path = str(p.parent / f"{p.stem}_FIXED{p.suffix}")

    mesh_fixed.export(output_path)

    return {
        "input": file_path,
        "output": output_path,
        "before": original_stats,
        "after": {
            "vertices": len(mesh_fixed.vertices),
            "faces": len(mesh_fixed.faces),
            "watertight": mesh_fixed.is_watertight,
            "non_manifold_edges": _count_non_manifold(mesh_fixed),
        },
    }


def scale(
    file_path: str,
    factor: float | None = None,
    target_mm: dict | None = None,
    output_path: str | None = None,
) -> dict:
    """Scale a mesh uniformly by factor or to target dimensions in mm.

    Args:
        file_path: Path to the STL file.
        factor: Uniform scale factor (e.g. 0.591 for 59.1%).
        target_mm: Target dimensions {"x": mm, "y": mm, "z": mm} — scales
                   uniformly to fit the largest axis.
        output_path: Where to save. Defaults to <name>_scaled.stl.
    """
    mesh = trimesh.load(file_path)

    # Detect meters and convert to mm
    if all(e < 1.0 for e in mesh.extents):
        mesh.apply_scale(1000.0)

    original_extents = mesh.extents.copy()

    if factor is not None:
        mesh.apply_scale(factor)
    elif target_mm is not None:
        ratios = []
        for i, axis in enumerate(["x", "y", "z"]):
            if axis in target_mm and target_mm[axis] > 0:
                ratios.append(target_mm[axis] / mesh.extents[i])
        if ratios:
            mesh.apply_scale(min(ratios))
    else:
        return {"error": "Provide either 'factor' or 'target_mm'"}

    if output_path is None:
        p = Path(file_path)
        output_path = str(p.parent / f"{p.stem}_scaled{p.suffix}")

    mesh.export(output_path)

    return {
        "input": file_path,
        "output": output_path,
        "original_mm": {
            "x": round(float(original_extents[0]), 2),
            "y": round(float(original_extents[1]), 2),
            "z": round(float(original_extents[2]), 2),
        },
        "scaled_mm": {
            "x": round(float(mesh.extents[0]), 2),
            "y": round(float(mesh.extents[1]), 2),
            "z": round(float(mesh.extents[2]), 2),
        },
        "factor_applied": round(float(mesh.extents[0] / original_extents[0]), 4),
    }


def rotate(
    file_path: str,
    axis: str = "x",
    angle_degrees: float = 90,
    output_path: str | None = None,
) -> dict:
    """Rotate a mesh around an axis."""
    mesh = trimesh.load(file_path)

    axis_map = {
        "x": [1, 0, 0],
        "y": [0, 1, 0],
        "z": [0, 0, 1],
    }
    if axis.lower() not in axis_map:
        return {"error": f"Invalid axis '{axis}'. Use x, y, or z."}

    angle_rad = math.radians(angle_degrees)
    rotation = trimesh.transformations.rotation_matrix(
        angle_rad, axis_map[axis.lower()]
    )
    mesh.apply_transform(rotation)

    if output_path is None:
        p = Path(file_path)
        output_path = str(p.parent / f"{p.stem}_rotated{p.suffix}")

    mesh.export(output_path)

    return {
        "input": file_path,
        "output": output_path,
        "axis": axis,
        "angle_degrees": angle_degrees,
        "extents_mm": {
            "x": round(float(mesh.extents[0]), 2),
            "y": round(float(mesh.extents[1]), 2),
            "z": round(float(mesh.extents[2]), 2),
        },
    }


def mirror(
    file_path: str,
    axis: str = "x",
    output_path: str | None = None,
) -> dict:
    """Mirror a mesh along an axis (e.g. right hand → left hand)."""
    mesh = trimesh.load(file_path)

    axis_idx = {"x": 0, "y": 1, "z": 2}.get(axis.lower())
    if axis_idx is None:
        return {"error": f"Invalid axis '{axis}'. Use x, y, or z."}

    matrix = np.eye(4)
    matrix[axis_idx, axis_idx] = -1
    mesh.apply_transform(matrix)
    # Fix inverted normals after mirroring
    mesh.invert()

    if output_path is None:
        p = Path(file_path)
        output_path = str(p.parent / f"{p.stem}_mirrored{p.suffix}")

    mesh.export(output_path)

    return {
        "input": file_path,
        "output": output_path,
        "axis": axis,
        "extents_mm": {
            "x": round(float(mesh.extents[0]), 2),
            "y": round(float(mesh.extents[1]), 2),
            "z": round(float(mesh.extents[2]), 2),
        },
    }


def calculate_scale(
    model_extents_mm: dict,
    target_circumference_mm: float | None = None,
    target_length_mm: float | None = None,
    clearance_pct: float = 5.0,
) -> dict:
    """Calculate ideal scale factor given patient measurements and model dimensions.

    Args:
        model_extents_mm: Model dimensions {"x": mm, "y": mm, "z": mm}.
        target_circumference_mm: Patient circumference (e.g. forearm).
        target_length_mm: Patient length measurement.
        clearance_pct: Clearance percentage to add (default 5%).
    """
    scales = []
    details = {}

    if target_length_mm is not None:
        # Assume Z is the length axis (longest)
        longest = max(model_extents_mm.values())
        s = target_length_mm / longest
        scales.append(s)
        details["by_length"] = round(s * 100, 1)

    if target_circumference_mm is not None:
        diameter = target_circumference_mm / math.pi
        # Assume X is the width axis
        width = model_extents_mm.get("x", 0)
        if width > 0:
            s = diameter / width
            scales.append(s)
            details["by_circumference"] = round(s * 100, 1)

    if not scales:
        return {"error": "Provide at least target_circumference_mm or target_length_mm"}

    base_scale = max(scales)
    clearance_factor = 1 + clearance_pct / 100
    final_scale = base_scale * clearance_factor

    result_extents = {
        k: round(v * final_scale, 1) for k, v in model_extents_mm.items()
    }

    return {
        "base_scale_pct": round(base_scale * 100, 1),
        "clearance_pct": clearance_pct,
        "final_scale_pct": round(final_scale * 100, 1),
        "final_scale_factor": round(final_scale, 4),
        "detail": details,
        "result_extents_mm": result_extents,
    }
