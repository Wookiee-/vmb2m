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

## RTV/RTM Settings

Configured under `"rtvrtm"` in your instance JSON or in `configs/rtvrtm.template`.

### General settings

| Field | Default | Description |
|---|---|---|
| `flood protection` | `3` | Seconds between commands per player. 0 = disabled |
| `use say only` | `0` | 1 = all messages via `say` (brief), 0 = important via `svsay` (chat box) |
| `name protection` | `1` | Kick players using reserved names "Server" or "Admin" |
| `default game` | `` | Map/mode to switch to when player count hits 0 |
| `clean log` | `2 10` | 0=off, 1=clean, 2=compress+clean. Second value is max MB |

### RTV (Rock the Vote)

| Field | Default | Description |
|---|---|---|
| `rtv` | `1` | 0 = disabled, 1 = enabled |
| `rtv rate` | `50` | % of players needed to trigger RTV. 0 = absolute majority |
| `rtv voting` | `0 3` | Voting completion: 0 = minutes, 1 = rounds |
| `rtv minimum votes` | `10` | Min % of votes for RTV not to fail. 0 = never fails |
| `rtv extend` | `2` | "Don't change" option: 0=never, 1=until limit, 2=always |
| `rtv successful/failed wait time` | `300` | Seconds before RTV can be used again after success/failure |
| `rtv skip voting` | `1` | 0=no skip, 1=skip when all voted, 2=skip when unreachable |
| `rtv second turn` | `1` | Runoff vote if no option gets >50% |
| `rtv change immediately` | `0` | 1 = change map immediately, 0 = wait for next round |

### RTM (Rock the Mode)

| Field | Default | Description |
|---|---|---|
| `rtm` | `0` | 0=off, 1=Open, 2=Semi, 4=Open+Semi, 8=Duel, 15=Legends, 21=All |
| `mode priority` | `2 0 2 0 2 1` | Priority for Open, Semi, Full, Duel, Legends, Extend |
| `rtm rate` | `0` | % of players needed. 0 = absolute majority |
| `rtm voting` | `0 3` | Voting completion: 0 = minutes, 1 = rounds |
| `rtm minimum votes` | `20` | Min % of votes for RTM not to fail |
| `rtm extend` | `2` | "Don't change" option behavior |
| `rtm successful/failed wait time` | `300` | Cooldown after success/failure |
| `rtm skip voting` | `1` | Skip when all voted or unreachable |
| `rtm second turn` | `0` | Runoff vote mode |
| `rtm change immediately` | `1` | Change mode immediately or next round |

### Map settings

| Field | Default | Description |
|---|---|---|
| `automatic maps` | `0` | 1 = auto-detect all BSP maps from pk3 files |
| `pick secondary maps` | `1` | 0=off, 1=secondary to fill gaps, 2=primary+secondary equally |
| `map priority` | `2 0 1` | Priority for primary, secondary, extend maps |
| `nomination type` | `0` | 0=one nom per player (max 5), 1=numbered votes for noms |
| `enable recently played maps` | `1800` | Seconds a map stays blocked after being played. 0=off |

### Admin voting

| Field | Default | Description |
|---|---|---|
| `admin voting` | `0 2` | 0=minutes, 1=rounds |
| `admin minimum votes` | `10` | % needed for admin votes to pass |
| `admin skip voting` | `1` | Skip when unreachable |

### Map limits (roundlimit/timelimit)

| Field | Default | Description |
|---|---|---|
| `roundlimit` | `0` | Start map vote when roundlimit is reached |
| `timelimit` | `0` | Start map vote when timelimit is reached |
| `limit voting` | `0 2` | Map limit voting timeout format |
| `limit extend` | `2` | "Don't change" for limit-triggered votes |
| `limit change immediately` | `0` | Change map immediately after limit vote |

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
