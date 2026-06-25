# Valzhar's MBII Manager

Server instance management, config generation, and plugin system for Movie Battles II.

## Quick start

```bash
./install.sh
cp configs/example.json configs/my_server.json
nano configs/my_server.json
mbii my_server start
```

## Commands

| Action | Command |
|---|---|
| Start server | `mbii <name> start` |
| Stop server | `mbii <name> stop` |
| Restart server | `mbii <name> restart` |
| Check status | `mbii <name> status` |
| List instances | `mbii --list` |
| Update MBII | `mbii --update` |

## Layout

```
configs/              # Per-instance JSON configs + templates
plugins/
  rtvrtm/             # Rock the Vote / Rock the Mode
  automessage/        # Rotating chat messages
  vpnmonitor/         # VPN/proxy detection
manager.py            # Boot, process control, auto-restart
updater/              # MBII CLI updater files
```

## Config

Each server instance has its own JSON file in `configs/`. See `example.json` as a starting point. Generated files go directly into your MBII folder.

## Plugins

Plugins are enabled in your instance JSON under `"plugins"`. `true` enables with defaults, a dict overrides specific settings.
