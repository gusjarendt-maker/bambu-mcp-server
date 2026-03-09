# bambu-mcp-server

> Built with [codrsync.dev](https://www.codrsync.dev)

MCP server for Bambu Lab 3D printing — from broken STL to printed part, all via Claude.

## Features

### Phase 1 — Mesh Tools
- **mesh_analyze** — Dimensions, vertices, faces, watertight status, non-manifold edges
- **mesh_repair** — Fix non-manifold edges, holes, and normals (pymeshfix)
- **mesh_scale** — Scale by factor or to target dimensions (auto-detects meters vs mm)
- **mesh_rotate** — Rotate around any axis
- **mesh_mirror** — Mirror along any axis (e.g. right hand to left hand)
- **mesh_calculate_scale** — Calculate ideal scale from real-world measurements

### Phase 2 — Slicer Integration (current)
- **slicer_detect** — Detect Bambu Studio installation, version, and profile locations
- **slicer_list_profiles** — List available profiles (machine, filament, process) from system and user
- **slicer_slice** — Slice STL/3MF to G-code with profile selection
- **slicer_export_3mf** — Package model + print settings as 3MF
- **slicer_model_info** — Get model information via Bambu Studio CLI

### Planned
- **Phase 3** — Printer control via MQTT (status, send, pause, speed)
- **Phase 4** — Project management (3MF parsing, preset profiles)

## Installation

```bash
pip install bambu-mcp-server
```

Or from source:

```bash
git clone https://github.com/gusjarendt-maker/bambu-mcp-server.git
cd bambu-mcp-server
pip install -e .
```

## Usage with Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "bambu": {
      "command": "bambu-mcp-server"
    }
  }
}
```

## Usage with Claude Code

```bash
claude mcp add bambu-mcp-server -- bambu-mcp-server
```

## Example Workflows

### Repair a broken STL
> "Analyze and repair this STL file: /path/to/model.stl"

### Scale a model for a specific person
> "This brace is 96x63x207mm. Scale it for someone with 170mm forearm circumference and 100mm length, with 5% clearance."

### Mirror a model
> "Mirror this right-hand splint to make a left-hand version"

### Slice a model for printing
> "Slice this STL using my H2D printer with PLA Basic filament at 0.20mm Standard quality"

### Export a ready-to-print 3MF
> "Package this repaired STL as a 3MF with H2D settings and PLA filament"

### Check slicer setup
> "Detect my Bambu Studio installation and list available profiles for H2D"

## Development

```bash
git clone https://github.com/gusjarendt-maker/bambu-mcp-server.git
cd bambu-mcp-server
pip install -e ".[dev]"
python -m pytest tests/
```

## License

MIT
