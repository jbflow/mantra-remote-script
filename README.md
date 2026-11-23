# Mantra Remote Script

Python-based Ableton Live Remote Script that interprets **Musical Intent Protocol (MIP)** intents via WebSocket from the Mantra Engine.

## Overview

Mantra Remote Script is an Ableton Live Remote Script that:
- Listens on a WebSocket server for MIP intents from the Mantra Engine
- Translates MIP intents into Ableton Live actions
- Maintains focus state and undo/redo functionality
- Provides real-time feedback on intent execution

## Architecture

```
Mantra Frontend (NextJS)
       ↓
Mantra Engine (TypeScript)
  - Parses natural language → MIP intents
       ↓
Mantra Remote Script (Python)
  - Listens on WebSocket
  - Executes intents in Ableton Live
```

## Quick Start

1. **Install**: Follow [INSTALL.md](./INSTALL.md) to set up the script in Ableton Live
2. **Start**: Enable the script in Ableton preferences
3. **Connect**: Mantra Frontend connects to the WebSocket server (default: `ws://localhost:1978`)
4. **Send Intents**: Send MIP intents via the WebSocket client

## Supported Domains

The script supports all MIP v0.2 domains:
- `transport` - Play, stop, record, tempo, time navigation
- `structure` - Track/clip creation, deletion, naming
- `music` - Notes, quantization, transposition
- `performance` - Scene/clip triggering
- And many more...

See [ARCHITECTURE.md](./ARCHITECTURE.md) for full domain mappings.

## Development

### Project Structure

```
├── Mantra.py              # Entry point, main script handler
├── IntentRouter.py        # Routes intents to handlers
├── DomainHandlers.py      # Domain-specific action handlers
├── Socket.py              # WebSocket server implementation
├── FocusState.py          # Maintains session focus state
├── Logging.py             # Structured logging
├── Utilities/
│   ├── KeyService.py      # Key/scale tracking
│   ├── TrackService.py    # Track queries
│   ├── BrowserService.py  # Browser navigation
│   └── MatcherService.py  # Pattern matching
└── ws_client.py           # Test WebSocket client
```

### Manual Testing

Use `ws_client.py` to send test intents:

```bash
python ws_client.py
# Then type: play
# Or: set tempo to 120
# Or: mute bass
```

## Configuration

WebSocket server runs on `localhost:1978` by default. Configure in `Socket.py`:

```python
PORT_RANGE = (1978, 1979)  # Try ports 1978-1979
```

## Dependencies

- Python 3.6+
- Ableton Live 11+
- `websockets` library (built into Live's Python)

## Troubleshooting

See [INSTALL.md](./INSTALL.md) for installation troubleshooting.

For runtime issues:
1. Check Ableton's status bar for error messages
2. Review `~/Music/Ableton User Library/Preferences/Log.txt`
3. Enable debug logging in `Logging.py`

## License

MIT
