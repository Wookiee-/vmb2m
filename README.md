# Valzhar's MBII Manager

Multi-instance MBII server manager with plugin system, config generation, and process control.

## Features

- Per-instance JSON configs with template-based server.cfg generation
- Auto-detects MBII folder and engine binary
- mimalloc memory allocator (Linux: LD_PRELOAD, Windows: side-by-side DLL)
- Plugin system (native + standalone)
- RTV/RTM voting, auto-messages, VPN monitor
- Process watchdog with auto-restart on crash
- MBII updater integration with retry logic
- Cross-platform: Linux (Debian, Fedora, Arch) and Windows

## Quick start

```bash
./install.sh                          # Installs deps, .NET, symlinks
cp configs/example.json configs/my_server.json
nano configs/my_server.json           # Set name, port, passwords, maps
mbii my_server start                  # Start server
```

## Commands

| Action | Command |
|---|---|
| Start | `mbii <name> start` |
| Stop | `mbii <name> stop` |
| Restart | `mbii <name> restart` |
| Status | `mbii <name> status` |
| List | `mbii --list` |
| Update MBII | `mbii --update` |

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

## Config

Each server has its own JSON in `configs/`. Generated files (server.cfg, map lists, rtvrtm.cfg) go directly into your MBII folder. `mbii_path` and `engine` auto-detect if not set.

## Plugins

Enable in your instance JSON under `"plugins"`. Use `true` for defaults or a dict to override settings. Each plugin lives in its own folder under `plugins/`.

## Installer

`install.sh` detects your distro and installs the correct packages:

| Distro | 32-bit libs | mimalloc |
|---|---|---|
| Debian/Ubuntu | `apt` | `libmimalloc-dev:i386` |
| Fedora/RHEL | `dnf` | `mimalloc.i686` |
| Arch | `pacman` | `lib32-mimalloc` |
| Windows | `install.bat` | DLLs copied to openjk folder |
