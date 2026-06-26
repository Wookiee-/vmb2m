# Valzhar's MBII Manager

Multi-instance MBII server manager with plugin system, config generation, and process control.

## Features

- Per-instance JSON configs with template-based server.cfg generation
- Auto-detects MBII folder and engine binary
- mimalloc memory allocator (Linux: LD_PRELOAD, Windows: side-by-side DLL)
- Plugin system (native + standalone)
- RTV/RTM voting, auto-messages, VPN monitor
- Process watchdog with auto-restart on crash and scheduled restart (configurable hours)
- MBII updater integration with retry logic
- Cross-platform: Linux (Debian, Fedora, Arch) and Windows

---

## Linux Setup

### 1. Install dependencies

```bash
git clone https://github.com/Wookiee-/vmb2m.git
cd vmb2m
./install.sh
```

This installs everything needed: Python 3, 32-bit libraries, mimalloc, .NET SDK 6.0, MBII updater files, and the `mbii` command shortcut.

### 2. Configure your server

```bash
cp configs/example.json configs/my_server.json
nano configs/my_server.json
```

Change at minimum:
- `host_name` — your server name
- `port` — server port (default 29070)
- `rcon_password` — choose a secure password
- `maps.primary` — your map list

The `mbii_path` and `engine` fields auto-detect if left empty.

### 3. Start the server

```bash
mbii my_server start
```

The server runs in the foreground. Auto-restarts on crash (up to 5 times). Press Ctrl+C to stop.

### 4. Stop the server

```bash
mbii my_server stop
```

---

## Windows Setup

### 1. Install Python 3

Download from https://python.org — check "Add Python to PATH" during install.

### 2. Download the manager

Download or clone the repo, or download the ZIP from GitHub.

### 3. Install .NET SDK 6.0 (required for MBII updates)

Download from: https://dotnet.microsoft.com/en-us/download/dotnet/6.0

Or via winget:
```
winget install Microsoft.DotNet.SDK.6
```

### 4. Configure your server

Copy `configs\example.json` to `configs\my_server.json` and edit it. Set your server name, port, passwords, and maps.

### 5. Start the server

```cmd
python manager.py my_server start
```

Press Ctrl+C to stop.

### 6. Stop the server

```cmd
python manager.py my_server stop
```

---

## Commands

| Action | Linux | Windows |
|---|---|---|
| Start server | `mbii <name> start` | `python manager.py <name> start` |
| Stop server | `mbii <name> stop` | `python manager.py <name> stop` |
| Restart server | `mbii <name> restart` | `python manager.py <name> restart` |
| Check status | `mbii <name> status` | `python manager.py <name> status` |
| List instances | `mbii --list` | `python manager.py --list` |


---

## Scheduled restart

Set `"restart_every_hours": 24` in your instance JSON. The manager will gracefully restart the engine every 24 hours to prevent memory leaks or performance degradation. Crash auto-restart still works independently.

---

## Multiple servers

Create one JSON file per server in `configs/`:

```bash
cp configs/example.json configs/eu_west.json
cp configs/example.json configs/us_east.json
# Edit each with different ports and settings
mbii eu_west start
mbii us_east start
```

---

## Plugins

Enable in your instance JSON under `"plugins"`:

```json
"plugins": {
    "rtvrtm": true,
    "automessage": {
        "messages": ["Welcome!"],
        "interval": 300
    },
    "vpnmonitor": {
        "apikey": "your_iphub_key"
    }
}
```

- `true` — enables with defaults
- `{ }` — enables with custom settings
- Omit or set `false` to disable

---

## Layout

```
configs/              # Per-instance JSON configs + templates
plugins/
  rtvrtm/             # Rock the Vote / Rock the Mode
  automessage/        # Rotating chat messages
  vpnmonitor/         # VPN/proxy detection
manager.py            # Boot, process control, auto-restart
mimalloc/             # mimalloc DLLs (Windows)
updater/              # MBII CLI updater files
```

---

## Distro support

| Distro | 32-bit libs | mimalloc |
|---|---|---|
| Debian/Ubuntu | `apt` | `libmimalloc-dev:i386` |
| Fedora/RHEL | `dnf` | `mimalloc.i686` |
| Arch | `pacman` | `lib32-mimalloc` |
