# Installation Guide

## Prerequisites

- Ableton Live 11 or later
- Python 3.6+ (comes with Ableton Live)
- Access to Ableton's User Library folder

## Installation Steps

### 1. Locate Your Ableton User Library

**macOS:**
```bash
~/Music/Ableton\ User\ Library/Remote\ Scripts/
```

**Windows:**
```
C:\Users\[YourUsername]\Music\Ableton User Library\Remote Scripts\
```

**Linux:**
```bash
~/Music/Ableton User Library/Remote Scripts/
```

### 2. Copy the Script

```bash
# macOS/Linux
cp -r mantra-remote-script ~/Music/Ableton\ User\ Library/Remote\ Scripts/mantra

# Windows (from PowerShell)
Copy-Item -Recurse mantra-remote-script -Destination "$env:USERPROFILE\Music\Ableton User Library\Remote Scripts\mantra"
```

Alternatively, create a symlink to allow live editing:

```bash
# macOS/Linux
ln -s /path/to/mantra-remote-script ~/Music/Ableton\ User\ Library/Remote\ Scripts/mantra
```

### 3. Enable in Ableton

1. Open Ableton Live Preferences
2. Go to **Link/MIDI** → **Control Surfaces**
3. In the dropdown under "Control Surface", select **Mantra**
4. Verify the Input/Output ports show "Mantra" (may appear as "Mantra" or generic port)

### 4. Verify Installation

After restarting Ableton:
1. Open the status bar or console
2. You should see: `Mantra Remote Script v0.1.0 initialized`
3. WebSocket server should be listening on `localhost:1978`

## Testing Connection

### From the Mantra Frontend

1. Start the frontend application
2. Try sending a simple command like "play"
3. Live should respond by starting playback

### Manual Testing with ws_client.py

```bash
cd mantra-remote-script
python ws_client.py

# In the interactive prompt, type:
play
set tempo to 120
mute bass
```

## Troubleshooting

### Script Not Appearing in Control Surfaces

**Problem**: Mantra doesn't show up in the Control Surfaces dropdown

**Solutions**:
1. Restart Ableton Live completely
2. Check the User Library folder path is correct
3. Verify the folder structure: `.../Remote Scripts/mantra/Mantra.py` exists
4. Check Live's error log: `~/Music/Ableton User Library/Preferences/Log.txt`

### WebSocket Connection Error

**Problem**: Frontend can't connect to the script

**Solutions**:
1. Verify Ableton is running and the script is enabled
2. Check if port 1978 is available: `lsof -i :1978` (macOS/Linux)
3. Try ports 1979-1980 (port_range in Socket.py)
4. Disable firewall temporarily to test

### Commands Not Working

**Problem**: Intents are received but not executing

**Solutions**:
1. Check Ableton's status bar for error messages
2. Review the Log.txt file for Python errors
3. Verify the intent format matches MIP v0.2 schema
4. Enable debug logging in `Logging.py`

### Script Crashes on Startup

**Problem**: Ableton crashes or disables the script immediately

**Solutions**:
1. Check for syntax errors: `python -m py_compile Mantra.py`
2. Verify all imports are available
3. Try a fresh copy of the script
4. Check Live's version compatibility (11.0+)

## Uninstallation

Simply delete the mantra folder from Remote Scripts:

```bash
# macOS/Linux
rm -rf ~/Music/Ableton\ User\ Library/Remote\ Scripts/mantra

# Windows (PowerShell)
Remove-Item -Recurse "$env:USERPROFILE\Music\Ableton User Library\Remote Scripts\mantra"
```

Then remove Mantra from Control Surfaces in Ableton preferences.

## Support

For issues and updates, see the main [README.md](./README.md) or check the project repository.
