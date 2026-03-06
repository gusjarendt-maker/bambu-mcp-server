"""Bambu MCP Server — mesh repair, slicing, and printer control for Bambu Lab.

Built with codrsync.dev (https://www.codrsync.dev)
"""

from __future__ import annotations

import json
from mcp.server.fastmcp import FastMCP

from bambu_mcp.tools import mesh

server = FastMCP(
    "bambu-mcp-server",
    version="0.1.0",
    description="MCP server for Bambu Lab 3D printing — mesh repair, slicing, and printer control.",
)


# ── Mesh Tools ──────────────────────────────────────────────────────────


@server.tool()
def mesh_analyze(file_path: str) -> str:
    """Analyze a 3D model file (STL/OBJ/3MF).

    Returns dimensions, vertex/face count, watertight status,
    non-manifold edge count, and volume.

    Args:
        file_path: Absolute path to the 3D model file.
    """
    result = mesh.analyze(file_path)
    return json.dumps(result, indent=2)


@server.tool()
def mesh_repair(file_path: str, output_path: str | None = None) -> str:
    """Repair a 3D model — fix non-manifold edges, holes, and normals.

    Uses pymeshfix for robust mesh repair. Returns before/after stats.

    Args:
        file_path: Absolute path to the input file.
        output_path: Where to save the repaired file. Defaults to <name>_FIXED.<ext>.
    """
    result = mesh.repair(file_path, output_path)
    return json.dumps(result, indent=2)


@server.tool()
def mesh_scale(
    file_path: str,
    factor: float | None = None,
    target_x_mm: float | None = None,
    target_y_mm: float | None = None,
    target_z_mm: float | None = None,
    output_path: str | None = None,
) -> str:
    """Scale a 3D model uniformly by factor or to fit target dimensions.

    If factor is given, applies uniform scaling (e.g. 0.591 = 59.1%).
    If target dimensions are given, scales uniformly to fit the smallest ratio.
    Automatically converts from meters to mm if needed.

    Args:
        file_path: Absolute path to the input file.
        factor: Uniform scale factor (e.g. 0.591 for 59.1%).
        target_x_mm: Target X dimension in mm.
        target_y_mm: Target Y dimension in mm.
        target_z_mm: Target Z dimension in mm.
        output_path: Where to save. Defaults to <name>_scaled.<ext>.
    """
    target_mm = {}
    if target_x_mm is not None:
        target_mm["x"] = target_x_mm
    if target_y_mm is not None:
        target_mm["y"] = target_y_mm
    if target_z_mm is not None:
        target_mm["z"] = target_z_mm

    result = mesh.scale(
        file_path,
        factor=factor,
        target_mm=target_mm if target_mm else None,
        output_path=output_path,
    )
    return json.dumps(result, indent=2)


@server.tool()
def mesh_rotate(
    file_path: str,
    axis: str = "x",
    angle_degrees: float = 90,
    output_path: str | None = None,
) -> str:
    """Rotate a 3D model around an axis.

    Args:
        file_path: Absolute path to the input file.
        axis: Rotation axis — "x", "y", or "z".
        angle_degrees: Rotation angle in degrees.
        output_path: Where to save. Defaults to <name>_rotated.<ext>.
    """
    result = mesh.rotate(file_path, axis, angle_degrees, output_path)
    return json.dumps(result, indent=2)


@server.tool()
def mesh_mirror(
    file_path: str,
    axis: str = "x",
    output_path: str | None = None,
) -> str:
    """Mirror a 3D model along an axis (e.g. right hand to left hand).

    Flips the model and fixes inverted normals.

    Args:
        file_path: Absolute path to the input file.
        axis: Mirror axis — "x", "y", or "z".
        output_path: Where to save. Defaults to <name>_mirrored.<ext>.
    """
    result = mesh.mirror(file_path, axis, output_path)
    return json.dumps(result, indent=2)


@server.tool()
def mesh_calculate_scale(
    model_x_mm: float,
    model_y_mm: float,
    model_z_mm: float,
    target_circumference_mm: float | None = None,
    target_length_mm: float | None = None,
    clearance_pct: float = 5.0,
) -> str:
    """Calculate ideal scale factor for a model given real-world measurements.

    Useful for scaling braces, splints, cases, or any object that must fit
    a specific body part or target dimension.

    Args:
        model_x_mm: Model width in mm.
        model_y_mm: Model depth in mm.
        model_z_mm: Model height/length in mm.
        target_circumference_mm: Target circumference (e.g. forearm, wrist).
        target_length_mm: Target length.
        clearance_pct: Extra clearance to add (default 5%).
    """
    result = mesh.calculate_scale(
        model_extents_mm={"x": model_x_mm, "y": model_y_mm, "z": model_z_mm},
        target_circumference_mm=target_circumference_mm,
        target_length_mm=target_length_mm,
        clearance_pct=clearance_pct,
    )
    return json.dumps(result, indent=2)


def main():
    """Run the MCP server."""
    server.run()


if __name__ == "__main__":
    main()
