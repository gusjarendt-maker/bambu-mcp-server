# bambu-mcp-server

> Built with [codrsync.dev](https://www.codrsync.dev)

MCP server for Bambu Lab 3D printing — from broken STL to printed part, all via Claude.

## Features

### Phase 1 — Mesh Tools (current)
- **mesh_analyze** — Dimensions, vertices, faces, watertight status, non-manifold edges
- **mesh_repair** — Fix non-manifold edges, holes, and normals (pymeshfix)
- **mesh_scale** — Scale by factor or to target dimensions (auto-detects meters vs mm)
- **mesh_rotate** — Rotate around any axis
- **mesh_mirror** — Mirror along any axis (e.g. right hand to left hand)
- **mesh_calculate_scale** — Calculate ideal scale from real-world measurements

### Planned
- **Phase 2** — Slicer integration (Bambu Studio CLI)
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

## Development

```bash
git clone https://github.com/gusjarendt-maker/bambu-mcp-server.git
cd bambu-mcp-server
pip install -e ".[dev]"
python -m pytest tests/
```

## License

MIT
