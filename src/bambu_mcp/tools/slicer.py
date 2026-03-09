"""Slicer tools — Bambu Studio CLI integration for slicing, profiles, and 3MF export."""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
from pathlib import Path


# ── Bambu Studio CLI Discovery ─────────────────────────────────────────

_BAMBU_PATHS = {
    "Darwin": [
        "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio",
        os.path.expanduser("~/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"),
        os.path.expanduser("~/Desktop/BambuStudio.app/Contents/MacOS/BambuStudio"),
    ],
    "Windows": [
        r"C:\Program Files\BambuStudio\bambu-studio.exe",
        r"C:\Program Files (x86)\BambuStudio\bambu-studio.exe",
    ],
    "Linux": [
        "/usr/bin/bambu-studio",
        "/usr/local/bin/bambu-studio",
        os.path.expanduser("~/.local/bin/bambu-studio"),
    ],
}

_PROFILE_BASE_PATHS = {
    "Darwin": [
        os.path.expanduser("~/Library/Application Support/BambuStudio"),
    ],
    "Windows": [
        os.path.expanduser("~/AppData/Roaming/BambuStudio"),
    ],
    "Linux": [
        os.path.expanduser("~/.config/BambuStudio"),
    ],
}


def _find_bambu_cli() -> str | None:
    """Find Bambu Studio CLI binary on the system."""
    system = platform.system()
    for path in _BAMBU_PATHS.get(system, []):
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def _find_profile_dirs() -> list[str]:
    """Find all Bambu Studio profile directories (system + user)."""
    system = platform.system()
    dirs = []
    for base in _PROFILE_BASE_PATHS.get(system, []):
        if os.path.isdir(base):
            dirs.append(base)

    # Also check inside the app bundle for system profiles (macOS)
    if system == "Darwin":
        app_profiles = "/Applications/BambuStudio.app/Contents/Resources/profiles"
        if os.path.isdir(app_profiles):
            dirs.append(app_profiles)

    return dirs


def _run_cli(args: list[str], timeout: int = 300) -> dict:
    """Run a Bambu Studio CLI command and return output."""
    cli = _find_bambu_cli()
    if cli is None:
        return {"error": "Bambu Studio not found. Install it or set BAMBU_CLI_PATH."}

    env = os.environ.copy()
    # Prevent GUI from launching on macOS
    env["QT_QPA_PLATFORM"] = "offscreen"

    cmd = [cli] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join(cmd),
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout}s", "command": " ".join(cmd)}
    except FileNotFoundError:
        return {"error": f"CLI binary not found at: {cli}"}


# ── Public Tools ───────────────────────────────────────────────────────


def detect() -> dict:
    """Detect Bambu Studio installation, version, and profile locations."""
    cli = _find_bambu_cli()
    profile_dirs = _find_profile_dirs()

    result = {
        "installed": cli is not None,
        "cli_path": cli,
        "platform": platform.system(),
        "profile_directories": profile_dirs,
    }

    if cli:
        # Try to get version from help output
        run = _run_cli(["--help"])
        if "error" not in run:
            # Version is typically in the first lines like "BambuStudio-02.03.01.51:"
            match = re.search(r"BambuStudio[- ]?([\d.]+)", run.get("stdout", "") + run.get("stderr", ""))
            if match:
                result["version"] = match.group(1)

    return result


def list_profiles(
    profile_type: str = "all",
    vendor: str = "BBL",
    include_user: bool = True,
) -> dict:
    """List available printing profiles (machine, filament, process).

    Args:
        profile_type: Type of profiles — "machine", "filament", "process", or "all".
        vendor: Vendor filter (default "BBL" for Bambu Lab). Use "all" for all vendors.
        include_user: Whether to include user-created profiles.
    """
    valid_types = {"machine", "filament", "process", "all"}
    if profile_type not in valid_types:
        return {"error": f"Invalid profile_type '{profile_type}'. Use: {', '.join(sorted(valid_types))}"}

    types_to_scan = ["machine", "filament", "process"] if profile_type == "all" else [profile_type]
    profiles: dict[str, list[dict]] = {}

    profile_dirs = _find_profile_dirs()
    if not profile_dirs:
        return {"error": "No Bambu Studio profile directories found."}

    for ptype in types_to_scan:
        profiles[ptype] = []

        for base_dir in profile_dirs:
            # System profiles: <base>/BBL/<type>/ or <base>/<vendor>/<type>/
            if vendor == "all":
                # Scan all vendor subdirectories
                vendors_to_scan = []
                for entry in Path(base_dir).iterdir():
                    if entry.is_dir() and (entry / ptype).is_dir():
                        vendors_to_scan.append(entry.name)
            else:
                vendors_to_scan = [vendor]

            for v in vendors_to_scan:
                type_dir = Path(base_dir) / v / ptype
                if type_dir.is_dir():
                    for f in sorted(type_dir.glob("*.json")):
                        profiles[ptype].append({
                            "name": f.stem,
                            "path": str(f),
                            "vendor": v,
                            "source": "system",
                        })

            # User profiles: <base>/user/<user_id>/<type>/
            if include_user:
                user_dir = Path(base_dir) / "user"
                if user_dir.is_dir():
                    for user_id in user_dir.iterdir():
                        type_dir = user_id / ptype
                        if type_dir.is_dir():
                            for f in sorted(type_dir.glob("*.json")):
                                profiles[ptype].append({
                                    "name": f.stem,
                                    "path": str(f),
                                    "vendor": "user",
                                    "source": f"user/{user_id.name}",
                                })

    # Summary counts
    summary = {ptype: len(items) for ptype, items in profiles.items()}

    return {
        "profiles": profiles,
        "summary": summary,
        "total": sum(summary.values()),
    }


def slice_model(
    file_path: str,
    machine_profile: str | None = None,
    filament_profile: str | None = None,
    process_profile: str | None = None,
    output_dir: str | None = None,
    plate: int = 0,
    enable_timelapse: bool = False,
) -> dict:
    """Slice a 3D model (STL/3MF) to G-code using Bambu Studio CLI.

    Args:
        file_path: Absolute path to the STL or 3MF file.
        machine_profile: Path to machine settings JSON, or None for default.
        filament_profile: Path to filament settings JSON, or None for default.
        process_profile: Path to process settings JSON, or None for default.
        output_dir: Directory for output files. Defaults to same directory as input.
        plate: Plate index to slice (0 = all plates).
        enable_timelapse: Enable timelapse for this slice.
    """
    if not os.path.isfile(file_path):
        return {"error": f"File not found: {file_path}"}

    args = [file_path, "--slice", str(plate)]

    # Build settings list
    settings_files = []
    if machine_profile:
        settings_files.append(machine_profile)
    if process_profile:
        settings_files.append(process_profile)
    if settings_files:
        args.extend(["--load-settings", ";".join(settings_files)])

    if filament_profile:
        args.extend(["--load-filaments", filament_profile])

    if output_dir is None:
        output_dir = str(Path(file_path).parent)
    args.extend(["--outputdir", output_dir])

    if enable_timelapse:
        args.append("--enable-timelapse")

    result = _run_cli(args)
    if "error" in result:
        return result

    # Find generated G-code files
    gcode_files = list(Path(output_dir).glob("*.gcode")) + list(Path(output_dir).glob("*.gcode.3mf"))
    # Get only files modified after slicing (within last 60s)
    import time
    now = time.time()
    recent_files = [f for f in gcode_files if (now - f.stat().st_mtime) < 60]

    return {
        "input": file_path,
        "output_dir": output_dir,
        "output_files": [str(f) for f in recent_files],
        "returncode": result["returncode"],
        "success": result["returncode"] == 0,
        "stdout": result["stdout"],
        "stderr": result["stderr"],
    }


def export_3mf(
    file_path: str,
    output_path: str | None = None,
    machine_profile: str | None = None,
    filament_profile: str | None = None,
    process_profile: str | None = None,
) -> dict:
    """Export/package a model as 3MF with embedded print settings.

    Args:
        file_path: Absolute path to the STL or 3MF file.
        output_path: Output 3MF path. Defaults to <name>.3mf in the same directory.
        machine_profile: Path to machine settings JSON.
        filament_profile: Path to filament settings JSON.
        process_profile: Path to process settings JSON.
    """
    if not os.path.isfile(file_path):
        return {"error": f"File not found: {file_path}"}

    if output_path is None:
        p = Path(file_path)
        output_path = str(p.parent / f"{p.stem}.3mf")

    args = [file_path, "--export-3mf", output_path]

    settings_files = []
    if machine_profile:
        settings_files.append(machine_profile)
    if process_profile:
        settings_files.append(process_profile)
    if settings_files:
        args.extend(["--load-settings", ";".join(settings_files)])

    if filament_profile:
        args.extend(["--load-filaments", filament_profile])

    result = _run_cli(args)
    if "error" in result:
        return result

    output_exists = os.path.isfile(output_path)

    return {
        "input": file_path,
        "output": output_path,
        "success": result["returncode"] == 0 and output_exists,
        "file_exists": output_exists,
        "file_size_bytes": os.path.getsize(output_path) if output_exists else 0,
        "stdout": result["stdout"],
        "stderr": result["stderr"],
    }


def model_info(file_path: str) -> dict:
    """Get model information through Bambu Studio CLI (dimensions, printability).

    Args:
        file_path: Absolute path to the STL or 3MF file.
    """
    if not os.path.isfile(file_path):
        return {"error": f"File not found: {file_path}"}

    result = _run_cli([file_path, "--info"])
    if "error" in result:
        return result

    return {
        "input": file_path,
        "success": result["returncode"] == 0,
        "info": result["stdout"],
        "stderr": result["stderr"],
    }


def export_settings(output_path: str | None = None) -> dict:
    """Export current Bambu Studio settings to a JSON file.

    Args:
        output_path: Where to save the settings file. Defaults to ./bambu_settings.json.
    """
    if output_path is None:
        output_path = "bambu_settings.json"

    result = _run_cli(["--export-settings", output_path])
    if "error" in result:
        return result

    output_exists = os.path.isfile(output_path)

    return {
        "output": output_path,
        "success": result["returncode"] == 0 and output_exists,
        "file_exists": output_exists,
        "stdout": result["stdout"],
        "stderr": result["stderr"],
    }
