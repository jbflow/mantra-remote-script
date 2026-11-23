# Mantra Remote Script Architecture

## Overview

Mantra Remote Script is a bridge between the Mantra Engine (TypeScript intent parser) and Ableton Live. It receives Musical Intent Protocol (MIP) intents via WebSocket and translates them into Live API calls.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Mantra Frontend                          │
│                    (NextJS / Browser)                       │
└───────────────────────────┬─────────────────────────────────┘
                            │
                    WebSocket (port 8080)
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Mantra Engine                            │
│              (TypeScript Intent Parser)                     │
│                                                             │
│  - parseTextToIntents()                                    │
│  - validateAndNormalize()                                 │
│  - MantraEngine (WebSocket client to Remote Script)       │
└───────────────────────────┬─────────────────────────────────┘
                            │
                    WebSocket (port 1978)
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Mantra Remote Script (Python)                  │
│                   Ableton Live 11+                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Socket.py - WebSocket Server                      │   │
│  │  Listens on localhost:1978                         │   │
│  └────────────────────┬────────────────────────────────┘   │
│                       │                                     │
│  ┌────────────────────▼────────────────────────────────┐   │
│  │  IntentRouter.py - Routes to Domain Handlers       │   │
│  │  Dispatches intents by domain                      │   │
│  └────────────────────┬────────────────────────────────┘   │
│                       │                                     │
│  ┌────────────────────▼────────────────────────────────┐   │
│  │  DomainHandlers.py - Domain-Specific Actions       │   │
│  │  Implements transport, structure, music, etc.      │   │
│  └────────────────────┬────────────────────────────────┘   │
│                       │                                     │
│  ┌────────────────────▼────────────────────────────────┐   │
│  │ Ableton Live API                                   │   │
│  │ Executes transport, track, clip, device actions    │   │
│  └───────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Socket.py - WebSocket Server

**Responsibility**: Listen for incoming MIP intents and dispatch them

**Key Classes**:
- `WebSocketServer` - Manages connections
- `ClientHandler` - Handles individual client connections

**Message Flow**:
1. Receives `{"type": "intent", "payload": <Intent>, "source": <Source>}`
2. Sends back `{"type": "ack", "ids": [<id>]}`
3. After processing, sends `{"type": "result", "id": <id>, "status": "ok"}`

**Error Handling**:
- Sends `{"type": "error", "code": "...", "message": "...", "issues": [...]}`

### 2. IntentRouter.py - Intent Dispatcher

**Responsibility**: Route intents to appropriate domain handlers

**Method**: `route(intent: Intent) -> Result`

**Flow**:
1. Extract `intent.domain` (e.g., "transport", "structure")
2. Look up handler in `DomainHandlers`
3. Call handler with intent payload
4. Return result status

### 3. DomainHandlers.py - Domain-Specific Implementations

**Responsibility**: Implement actual Ableton Live actions for each MIP domain

**Supported Domains**:

#### Transport (`transport`)
- `play` - Start playback
- `stop` - Stop playback
- `record` - Toggle record
- `set_tempo` - Change BPM
- `locate` - Jump to time position
- `metronome_on/off` - Toggle click
- `loop_on/off` - Toggle loop
- `set_loop` - Set loop points

#### Structure (`structure`)
- `create_track` - Create new track
- `select_track` - Focus track
- `mute` - Toggle mute
- `solo` - Toggle solo
- `arm_track` - Arm for recording
- `rename_track` - Change track name
- `load_device` - Add plugin to track

#### Music (`music`)
- `add_notes` - Insert notes into clip
- `quantize` - Quantize notes
- `transpose` - Shift pitch
- `set_key_signature` - Set track key

#### Performance (`performance`)
- `launch_scene` - Trigger scene
- `launch_clip` - Trigger clip

**Example Handler**:
```python
def handle_transport_play(intent):
    song = live_instance().song
    song.is_playing = True
    return {"status": "ok"}
```

### 4. FocusState.py - Session State Management

**Responsibility**: Track which track/clip/device is currently focused

**State**:
```python
{
  "selected_track": Track,
  "selected_clip": Clip,
  "selected_device": Device,
  "current_key": str,
  "time_signature": tuple
}
```

**Use Cases**:
- Remember last muted track (for undo)
- Apply edits to focused track
- Maintain context between intents

### 5. Utility Services

#### KeyService.py
- Track and validate musical key signatures
- Transpose notes relative to key
- Validate scale degrees

#### TrackService.py
- Find tracks by name/index
- Query track properties
- Manage track selection

#### BrowserService.py
- Navigate Ableton's browser
- Load devices/samples by name
- Handle search queries

#### MatcherService.py
- Pattern match track/device names
- Fuzzy matching for user input
- Resolve ambiguous references

### 6. Logging.py - Structured Logging

**Output**: Writes to Ableton's Log.txt

**Format**: JSON with timestamp, level, component, message

```json
{"timestamp": "2026-11-23T21:00:00Z", "level": "INFO", "component": "Socket", "message": "Client connected"}
```

## Message Protocol

### Client → Server (Mantra Frontend)

**Intent Message**:
```json
{
  "type": "intent",
  "payload": {
    "domain": "transport",
    "intent": {"action": "play"}
  },
  "source": "frontend"
}
```

**Ping Message** (keep-alive):
```json
{
  "type": "ping"
}
```

### Server → Client (Mantra Remote Script)

**Acknowledgment**:
```json
{
  "type": "ack",
  "ids": ["intent-uuid-1"],
  "status": "accepted"
}
```

**Result** (after execution):
```json
{
  "type": "result",
  "id": "intent-uuid-1",
  "status": "ok",
  "details": {
    "action": "play",
    "tempo_before": 120,
    "tempo_after": 120
  }
}
```

**Error**:
```json
{
  "type": "error",
  "code": "VALIDATION_ERROR",
  "message": "Invalid intent payload",
  "issues": [{"path": "intent.action", "message": "unknown action"}]
}
```

## Pong Response
```json
{
  "type": "pong"
}
```

## Data Flow Example

**Input**: User says "play" in Mantra Frontend

```
1. Frontend: "play" → Mantra Engine
2. Engine: parseTextToIntents("play") → Intent
3. Engine: sends Intent via MantraEngine WebSocket client
4. Remote Script receives:
   {
     "type": "intent",
     "payload": {"domain": "transport", "intent": {"action": "play"}}
   }
5. Socket.py parses message
6. IntentRouter.route(intent) → calls DomainHandlers.handle_transport_play()
7. DomainHandlers calls: live_instance().song.is_playing = True
8. Socket.py sends back:
   {"type": "result", "id": "...", "status": "ok"}
```

## Error Handling

### Validation Errors
- Intent doesn't match MIP schema
- Response: `{"type": "error", "code": "VALIDATION_ERROR", ...}`

### Domain Errors
- Unknown domain or action
- Response: `{"type": "error", "code": "BAD_REQUEST", ...}`

### Execution Errors
- Ableton Live API call fails (track doesn't exist, etc.)
- Response: `{"type": "error", "code": "INTERNAL_ERROR", ...}`

## State Management

### Per-Intent State
- `FocusState` tracks which track/clip/device an intent targets
- Used by handlers to apply edits to the right context

### Session State
- Key signature for music domain
- Time signature
- Selected track (for shortcuts)

### Undo/Redo
- Each intent handler pushes changes to Live's undo stack
- Users can undo intent effects in Live UI

## Performance Considerations

1. **Async Execution**: All handlers execute synchronously (Ableton limitation)
2. **Batch Processing**: Support multiple intents in one message
3. **Caching**: TrackService caches track lookups for 100ms
4. **Fuzzy Matching**: MatcherService uses efficient Levenshtein distance

## Extension Points

### Adding a New Domain

1. Add handler to `DomainHandlers.py`:
   ```python
   def handle_newdomain_action(intent):
       # Implementation
       return {"status": "ok"}
   ```

2. Register in `IntentRouter.py`:
   ```python
   "newdomain": {
       "action": handle_newdomain_action
   }
   ```

3. Test via `ws_client.py`

### Adding a New Action

1. Create handler function in domain section
2. Register in action map
3. Test with actual Ableton instance

## Testing Strategy

1. **Unit Tests**: Test handlers in isolation (mocked Live API)
2. **Integration Tests**: Test with actual Ableton Live instance
3. **Manual Testing**: Use `ws_client.py` for interactive testing

## Known Limitations

- Python 3.6+ only (Ableton Live constraint)
- Single-threaded (Live API is not thread-safe)
- No persistent storage of state
- Limited to MIP v0.2 schema

## Future Improvements

- Batch intent processing
- Intent macros/sequences
- Learning from user corrections
- Undo/redo stack visualization
- Performance metrics dashboard
