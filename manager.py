#!/usr/bin/env python3
"""
MBII Server Manager — config, boot, process control, auto-restart.
"""

import configparser
import json
import os
import platform
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")

class C:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    END = "\033[0m"

def ok(msg):
    print("  %s[OK]%s %s" % (C.GREEN, C.END, msg))

def warn(msg):
    print("  %s[WARN]%s %s" % (C.YELLOW, C.END, msg))

def fail(msg):
    print("  %s[ERROR]%s %s" % (C.RED, C.END, msg))

def info(msg):
    print("  %s%s%s" % (C.CYAN, msg, C.END))

if not IS_WINDOWS and not IS_LINUX:
    print("[WARN] Unsupported OS: %s, Windows/Linux features may not work" % sys.platform)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plugins.manager import PluginManager
from plugins import event_types as events

BASE = Path(__file__).resolve().parent
PID_DIR = BASE / "pids"

MODE_MAP = {
    "open": "0", "semi-authentic": "1", "semi": "1",
    "full-authentic": "2", "full": "2",
    "duel": "3", "legends": "4",
}
RTVRTM_FIELD_MAP = {
    "log": "logfile", "mbii folder": "MBII_Folder",
    "address": "address", "bind": "bindaddr",
    "password": "rcon_pwd", "flood protection": "flood_protection",
    "use say only": "use_say_only", "name protection": "name_protection",
    "default game": "default_game", "clean log": "clean_log",
    "admin voting": "admin_voting", "admin minimum votes": "admin_minimum_votes",
    "admin skip voting": "admin_skip_voting",
    "roundlimit": "roundlimit", "timelimit": "timelimit",
    "limit voting": "limit_voting", "limit minimum votes": "limit_minimum_votes",
    "limit extend": "limit_extend", "limit successful wait time": "limit_s_wait_time",
    "limit failed wait time": "limit_f_wait_time", "limit skip voting": "limit_skip_voting",
    "limit second turn": "limit_second_turn", "limit change immediately": "limit_change_immediately",
    "rtv": "rtv", "rtv rate": "rtv_rate", "rtv voting": "rtv_voting",
    "rtv minimum votes": "rtv_minimum_votes", "rtv extend": "rtv_extend",
    "rtv successful wait time": "rtv_s_wait_time", "rtv failed wait time": "rtv_f_wait_time",
    "rtv skip voting": "rtv_skip_voting", "rtv second turn": "rtv_second_turn",
    "rtv change immediately": "rtv_change_immediately",
    "automatic maps": "automatic_maps", "maps": "maps", "secondary maps": "secondary_maps",
    "pick secondary maps": "pick_secondary_maps", "map priority": "map_priority",
    "nomination type": "nomination_type", "enable recently played maps": "enable_recently_played",
    "rtm": "rtm", "mode priority": "mode_priority", "rtm rate": "rtm_rate",
    "rtm voting": "rtm_voting", "rtm minimum votes": "rtm_minimum_votes",
    "rtm extend": "rtm_extend", "rtm successful wait time": "rtm_s_wait_time",
    "rtm failed wait time": "rtm_f_wait_time", "rtm skip voting": "rtm_skip_voting",
    "rtm second turn": "rtm_second_turn", "rtm change immediately": "rtm_change_immediately",
}
def load_global_config():
    """Read mbii.conf for global defaults (paths, engine, game)."""
    conf = BASE / "mbii.conf"
    if not conf.exists():
        return {}
    cfg = configparser.ConfigParser()
    cfg.read(str(conf))
    result = {}
    if cfg.has_section("locations"):
        for key in ("mbii_path", "config_path"):
            val = cfg.get("locations", key, fallback="").strip()
            if val:
                result[key] = val
    if cfg.has_section("dedicated"):
        for key in ("engine", "game"):
            val = cfg.get("dedicated", key, fallback="").strip()
            if val:
                result[key] = val
    return result


GLOBAL_CFG = load_global_config()
CONFIG_DIR = Path(GLOBAL_CFG.get("config_path", "")) if GLOBAL_CFG.get("config_path") else BASE / "configs"


def merge_config(instance_cfg):
    """Apply global defaults, then instance overrides, then auto-detect."""
    cfg = dict(GLOBAL_CFG)
    # Apply per-instance server settings
    server = instance_cfg.get("server", {})
    for key in ("mbii_path", "engine", "game"):
        if key in server:
            cfg[key] = server[key]
        elif key not in cfg:
            cfg[key] = ""
    instance_cfg["server"].update(cfg)
    return instance_cfg


RTVRTM_DEFAULTS = {
    "flood protection": "3", "use say only": "0", "name protection": "1",
    "default game": "", "clean log": "2 10",
    "admin voting": "0 2", "admin minimum votes": "10", "admin skip voting": "1",
    "roundlimit": "0", "timelimit": "0",
    "limit voting": "0 2", "limit minimum votes": "10", "limit extend": "2",
    "limit successful wait time": "300", "limit failed wait time": "300",
    "limit skip voting": "1", "limit second turn": "1", "limit change immediately": "0",
    "rtv": "1", "rtv rate": "50", "rtv voting": "0 3", "rtv minimum votes": "10",
    "rtv extend": "2", "rtv successful wait time": "300", "rtv failed wait time": "300",
    "rtv skip voting": "1", "rtv second turn": "1", "rtv change immediately": "0",
    "automatic maps": "0", "pick secondary maps": "1", "map priority": "2 0 1",
    "nomination type": "0", "enable recently played maps": "1800",
    "rtm": "0", "mode priority": "2 0 2 0 2 1", "rtm rate": "0",
    "rtm voting": "0 3", "rtm minimum votes": "20", "rtm extend": "2",
    "rtm successful wait time": "300", "rtm failed wait time": "300",
    "rtm skip voting": "1", "rtm second turn": "0", "rtm change immediately": "1",
}


def load_config(name):
    path = CONFIG_DIR / ("%s.json" % name)
    if not path.exists():
        print("[ERROR] Config not found: %s" % path)
        sys.exit(1)
    with open(path) as f:
        cfg = json.load(f)
    cfg["name"] = name  # Filename always wins
    return merge_config(cfg)


def pid_path(name, label):
    PID_DIR.mkdir(parents=True, exist_ok=True)
    return PID_DIR / ("%s_%s.pid" % (name, label))


def read_pid(name, label):
    p = pid_path(name, label)
    if p.exists():
        try:
            with open(p) as f:
                return int(f.read().strip())
        except (ValueError, OSError):
            pass
    return None


def write_pid(name, label, pid):
    p = pid_path(name, label)
    with open(p, "w") as f:
        f.write(str(pid))


def remove_pid(name, label):
    p = pid_path(name, label)
    if p.exists():
        p.unlink()


def is_pid_alive(pid):
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, PermissionError):
        return False


def kill_pid(pid, sig=None):
    if pid is None or pid <= 0:
        return False
    if sig is None:
        sig = signal.SIGTERM if not IS_WINDOWS else signal.SIGTERM
    try:
        if IS_WINDOWS:
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
            if handle:
                ctypes.windll.kernel32.TerminateProcess(handle, 1)
                ctypes.windll.kernel32.CloseHandle(handle)
            return True
        else:
            os.kill(pid, sig)
            return True
    except (OSError, PermissionError, ImportError):
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           capture_output=True, timeout=5)
            return True
        except Exception:
            return False


RCON_PREFIX = bytes([0xff, 0xff, 0xff, 0xff])


class RCONClient:
    """UDP RCON connection to the game server."""

    def __init__(self, password, host="127.0.0.1", port=29070):
        self._addr = (host, port)
        self._password = password
        self._sock = None

    def connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(4)

    def disconnect(self):
        if self._sock:
            self._sock.close()
            self._sock = None

    def send(self, command):
        if not self._sock:
            return None
        cmd = RCON_PREFIX + b"rcon " + ("%s %s" % (self._password, command)).encode()
        try:
            self._sock.sendto(cmd, self._addr)
            data = self._sock.recv(4096)
            return data.decode("utf-8", errors="replace").strip()
        except socket.timeout:
            return None
        except OSError:
            return None

    def cvar(self, name, value=None):
        if value is not None:
            return self.send("set %s=%s" % (name, value))
        resp = self.send(name)
        if resp:
            m = re.search(r'"([^"]*)"', resp)
            if m:
                return m.group(1)
        return resp


class LogWatcher:
    """Reads the server log and fires events to the PluginManager."""

    PLAYER_RE = re.compile(r'^(\d+):\s+(.+?)\s+say:\s+"(.+)"')
    TEAM_RE = re.compile(r'^(\d+):\s+(.+?)\s+sayteam:\s+"(.+)"')
    KILL_RE = re.compile(r"Kill:\s+(\d+)\s+(\d+)\s+.+?: (.+?)(?: teamkilled)?$")
    CONNECT_RE = re.compile(r"ClientConnect:\s+(\d+)")
    DISCONNECT_RE = re.compile(r"ClientDisconnect:\s+(\d+)")
    BEGIN_RE = re.compile(r"ClientBegin:\s+(\d+)")
    MAP_RE = re.compile(r"InitGame:\\")
    EXIT_RE = re.compile(r"^Exit:")

    def __init__(self, log_path, plugin_mgr):
        self._path = log_path
        self._pm = plugin_mgr
        self._file = None

    def start(self):
        if not os.path.exists(self._path):
            return
        self._file = open(self._path, "r", encoding="utf-8", errors="replace")
        self._file.seek(0, 2)

    def stop(self):
        if self._file:
            self._file.close()
            self._file = None

    def poll(self):
        """Read new lines from log and dispatch events."""
        if not self._file:
            return
        lines = self._file.read()
        if not lines:
            return
        for raw in lines.split("\n"):
            line = raw.strip()
            if not line:
                continue
            self._parse_line(line)

    def _parse_line(self, line):
        m = self.PLAYER_RE.match(line)
        if m:
            e = events.PlayerChatEvent(m.group(1), m.group(2), m.group(3))
            self._pm.dispatch(e)
            return

        m = self.TEAM_RE.match(line)
        if m:
            e = events.PlayerChatEvent(m.group(1), m.group(2), m.group(3), team=True)
            self._pm.dispatch(e)
            return

        m = self.KILL_RE.match(line)
        if m:
            e = events.PlayerKillEvent(m.group(1), m.group(2), m.group(3))
            self._pm.dispatch(e)
            return

        if line.startswith("ShutdownGame"):
            self._pm.dispatch(events.Event(events.EVENT_SERVER_SHUTDOWN))
        elif line.startswith("ClientConnect:"):
            sp = line.split()
            pid = sp[1] if len(sp) > 1 else "0"
            ip = ""
            for token in sp:
                if token.count(".") >= 2 and ("@" in token or ":" in token):
                    ip = token.strip("@").rsplit(":", 1)[0]
                    break
            e = events.Event(events.EVENT_PLAYER_CONNECT, {"player_id": pid, "ip": ip})
            self._pm.dispatch(e)
        elif line.startswith("ClientDisconnect:"):
            e = events.Event(events.EVENT_PLAYER_DISCONNECT, {"player_id": line.split()[1]})
            self._pm.dispatch(e)
        elif line.startswith("ClientBegin:"):
            e = events.Event(events.EVENT_PLAYER_BEGIN, {"player_id": line.split()[1]})
            self._pm.dispatch(e)
        elif line.startswith("Exit:"):
            self._pm.dispatch(events.Event(events.EVENT_ROUND_EXIT))
        elif self.MAP_RE.match(line):
            map_name = ""
            if "\\mapname\\" in line:
                try:
                    map_name = line.split("\\mapname\\")[1].split("\\")[0]
                except IndexError:
                    pass
            self._pm.dispatch(events.Event(events.EVENT_MAP_CHANGE, {"map": map_name}))


def find_mimalloc():
    """Find i386 mimalloc library on Linux."""
    if not IS_LINUX:
        return None
    candidates = [
        "/usr/lib/i386-linux-gnu/libmimalloc.so.2",
        "/usr/lib/i386-linux-gnu/libmimalloc.so.1",
        "/usr/lib/i386-linux-gnu/libmimalloc.so",
        "/usr/lib/libmimalloc.so.2",
        "/usr/lib/libmimalloc.so.1",
        "/usr/lib/libmimalloc.so",
        "/usr/lib32/libmimalloc.so.2",
        "/usr/lib32/libmimalloc.so.1",
        "/usr/lib32/libmimalloc.so",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    try:
        out = subprocess.check_output(
            ["ldconfig", "-p"], stderr=subprocess.DEVNULL, universal_newlines=True
        )
        for line in out.splitlines():
            if "libmimalloc" in line and ".so" in line:
                parts = line.split("=>")
                if len(parts) == 2:
                    return parts[1].strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return None


def build_env(use_allocator=True):
    env = os.environ.copy()
    if IS_LINUX and use_allocator:
        lib_path = find_mimalloc()
        if lib_path:
            existing = env.get("LD_PRELOAD", "")
            env["LD_PRELOAD"] = "%s:%s" % (lib_path, existing) if existing else lib_path
            env["MIMALLOC_PAGE_RESET"] = "0"
            env["MIMALLOC_LARGE_OS_PAGES"] = "1"
    return env


def build_template_values(cfg):
    game = cfg["game"]
    sec = cfg["security"]
    smod = cfg["smod"]
    mode = MODE_MAP.get(game["mode"].lower(), "0")
    cl_parts = [str(v) for v in cfg.get("class_limits", {}).values()]
    return {
        "instance_name": cfg["name"],
        "host_name": cfg["server"]["host_name"],
        "message_of_the_day": game.get("message_of_the_day", "").replace("\n", "\\n"),
        "discord": cfg["server"].get("discord", ""),
        "rcon_password": sec["rcon_password"],
        "server_password": sec.get("server_password", ""),
        "log_name": "%s-games.log" % cfg["name"],
        "mode": mode,
        "starting_map": game["starting_map"],
        "map_win_limit": str(game["map_win_limit"]),
        "map_round_limit": str(game["map_round_limit"]),
        "competitive_config": str(game.get("competitive_config", 0)),
        "balance_mode": str(game.get("balance_mode", -1)),
        "admin_1_password": smod.get("admin_1", {}).get("password", ""),
        "admin_1_config": str(smod.get("admin_1", {}).get("config", 0)),
        "admin_2_password": smod.get("admin_2", {}).get("password", ""),
        "admin_2_config": str(smod.get("admin_2", {}).get("config", 0)),
        "admin_3_password": smod.get("admin_3", {}).get("password", ""),
        "admin_3_config": str(smod.get("admin_3", {}).get("config", 0)),
        "admin_4_password": smod.get("admin_4", {}).get("password", ""),
        "admin_4_config": str(smod.get("admin_4", {}).get("config", 0)),
        "admin_5_password": smod.get("admin_5", {}).get("password", ""),
        "admin_5_config": str(smod.get("admin_5", {}).get("config", 0)),
        "admin_6_password": smod.get("admin_6", {}).get("password", ""),
        "admin_6_config": str(smod.get("admin_6", {}).get("config", 0)),
        "admin_7_password": smod.get("admin_7", {}).get("password", ""),
        "admin_7_config": str(smod.get("admin_7", {}).get("config", 0)),
        "admin_8_password": smod.get("admin_8", {}).get("password", ""),
        "admin_8_config": str(smod.get("admin_8", {}).get("config", 0)),
        "admin_9_password": smod.get("admin_9", {}).get("password", ""),
        "admin_9_config": str(smod.get("admin_9", {}).get("config", 0)),
        "admin_10_password": smod.get("admin_10", {}).get("password", ""),
        "admin_10_config": str(smod.get("admin_10", {}).get("config", 0)),
        "class_limits": "-".join(cl_parts),
        "DuelMidRoundRespawnTimerInitial": "20",
        "DuelMidRoundRespawnTimerNoLives": "2",
        "DuelMidRoundRespawnTimerNoLivesIncrement": "2",
    }


def find_mbii():
    """Auto-detect MBII folder from common locations."""
    home = Path.home()
    candidates = []
    if IS_LINUX:
        candidates = [
            home / ".ja" / "MBII",
            home / ".local" / "share" / "openjk" / "MBII",
            Path("/home/mbiiez/openjk/MBII"),
            Path("/opt/openjk/MBII"),
        ]
    elif IS_WINDOWS:
        candidates = [
            Path("C:/Program Files (x86)/OpenJK/MBII"),
            Path("C:/Program Files/OpenJK/MBII"),
        ]
    for p in candidates:
        if (p / "MBII.pk3").exists() or (p / "assets1.pk3").exists():
            return p
    return None


def mbii_dir(cfg):
    path = cfg["server"].get("mbii_path", "")
    if not path:
        detected = find_mbii()
        if detected:
            path = str(detected)
            cfg["server"]["mbii_path"] = path
    return Path(path) if path else Path()


def generate_server_cfg(cfg):
    out_dir = mbii_dir(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    tpl = CONFIG_DIR / "server.template"
    if not tpl.exists():
        print("[ERROR] server.template not found")
        return None
    with open(tpl) as f:
        template = f.read()
    result = template
    for key, val in build_template_values(cfg).items():
        result = result.replace("[%s]" % key, val)
    out = out_dir / ("%s-server.cfg" % cfg["name"])
    with open(out, "w") as f:
        f.write(result)
    return out


def generate_map_files(cfg):
    out_dir = mbii_dir(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = cfg["name"]
    maps = cfg.get("maps", {})
    primary = out_dir / ("%s-maps.txt" % name)
    with open(primary, "w") as f:
        for m in maps.get("primary", []):
            f.write("%s\n" % m)
    secondary = out_dir / ("%s-secondary_maps.txt" % name)
    with open(secondary, "w") as f:
        for m in maps.get("secondary", []):
            f.write("%s\n" % m)


def generate_rtvrtm_cfg(cfg):
    out_dir = mbii_dir(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    rtv_raw = cfg.get("rtvrtm", {})
    rtv = rtv_raw if isinstance(rtv_raw, dict) else {}

    # Load template if it exists
    template_path = CONFIG_DIR / "rtvrtm.template"
    if template_path.exists():
        with open(template_path) as f:
            all_fields = {}
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, val = line.split(":", 1)
                    all_fields[key.strip().lower()] = val.strip()
    else:
        all_fields = dict(RTVRTM_DEFAULTS)

    # Override with any JSON settings
    all_fields.update({k: v for k, v in rtv.items() if v is not None})

    lines = [
        "* Generated from %s.json\n" % cfg["name"],
        "* DO NOT EDIT\n",
    ]
    lines.append("Log: %s\n" % (out_dir / ("%s-games.log" % cfg["name"])))
    lines.append("MBII folder: %s\n" % str(out_dir))
    lines.append("Address: 127.0.0.1:%s\n" % cfg["server"]["port"])
    lines.append("Bind: 127.0.0.1\n")
    lines.append("Password: %s\n" % cfg["security"]["rcon_password"])
    lines.append("Maps: %s\n" % (out_dir / ("%s-maps.txt" % cfg["name"])))
    lines.append("Secondary maps: %s\n" % (out_dir / ("%s-secondary_maps.txt" % cfg["name"])))
    for key in RTVRTM_FIELD_MAP:
        if key in all_fields:
            lines.append("%s: %s\n" % (key, all_fields[key]))
    out = out_dir / ("%s-rtvrtm.cfg" % cfg["name"])
    with open(out, "w") as f:
        f.writelines(lines)
    return out


def _engine_alive(name):
    """Check if engine process is actually running."""
    if IS_WINDOWS:
        pid = read_pid(name, "engine")
        return is_pid_alive(pid) if pid else False
    try:
        r = subprocess.run(["screen", "-list"], capture_output=True, timeout=5, text=True)
        if "mb2_%s" % name not in r.stdout:
            return False
        # Screen exists — verify engine binary is actually running inside it
        r2 = subprocess.run(["pgrep", "-f", "mbiided.*%s" % name],
                            capture_output=True, timeout=5)
        return r2.returncode == 0
    except Exception:
        return False


def _engine_exists(name):
    """Check if a screen session exists with a live engine inside."""
    try:
        r = subprocess.run(["screen", "-list"], capture_output=True, timeout=5, text=True)
        if "mb2_%s" % name not in r.stdout:
            return False
        r2 = subprocess.run(["pgrep", "-f", "mbiided.*%s" % name],
                            capture_output=True, timeout=5)
        return r2.returncode == 0
    except Exception:
        return False


def _engine_kill(name):
    """Kill a screen session for this instance."""
    if IS_WINDOWS:
        return
    try:
        subprocess.run(["screen", "-S", "mb2_%s" % name, "-X", "quit"],
                       capture_output=True, timeout=5)
        subprocess.run(["pkill", "-f", "mb2_%s" % name],
                       capture_output=True, timeout=5)
    except Exception:
        pass


def find_engine(cfg=None):
    """Auto-detect engine binary.
       Priority: PATH -> /usr/bin -> GameData dir.
    """
    name = "mbiided.x86.exe" if IS_WINDOWS else "mbiided.i386"

    for p in os.environ.get("PATH", "").split(os.pathsep):
        full = Path(p) / name
        if full.exists():
            return str(full)

    if not IS_WINDOWS:
        full = Path("/usr/bin") / name
        if full.exists():
            return str(full)

    if cfg:
        mbii = mbii_dir(cfg)
        gamedata = mbii.parent
        full = gamedata / name
        if full.exists():
            return str(full)

    return name


def start_engine(cfg):
    engine = cfg["server"].get("engine", "")
    if not engine:
        engine = find_engine(cfg)
        cfg["server"]["engine"] = engine
    port = cfg["server"]["port"]
    game = cfg["server"].get("game", "MBII")
    server_cfg = "%s-server.cfg" % cfg["name"]
    instance_dir = mbii_dir(cfg)
    screen_name = "mb2_%s" % cfg["name"]
    using_screen = False

    cmd = [
        engine,
        "--quiet",
        "+set", "dedicated", "2",
        "+set", "net_port", str(port),
        "+set", "fs_game", game,
        "+exec", server_cfg,
    ]

    if _engine_exists(cfg["name"]):
        return None
    # Clean up any stale/dead screen sessions for this name
    if not IS_WINDOWS:
        _engine_kill(cfg["name"])
        subprocess.run(["screen", "-wipe"], capture_output=True, timeout=5)

    env = build_env()
    if IS_WINDOWS:
        kwargs = {"cwd": str(instance_dir), "env": env,
                  "creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
    else:
        import shutil as _su
        if _su.which("screen"):
            using_screen = True
            cmd = ["screen", "-dmS", screen_name] + cmd
        kwargs = {"cwd": str(instance_dir), "env": env}

    print("  Engine: %s" % " ".join(cmd))
    if IS_LINUX and env.get("LD_PRELOAD") and "mimalloc" in env["LD_PRELOAD"]:
        print("  mimalloc: %s" % env["LD_PRELOAD"])

    if using_screen:
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
        write_pid(cfg["name"], "engine", 1)  # Dummy PID, checked via screen/port
        ok("Engine starting in screen: %s" % screen_name)
    else:
        proc = subprocess.Popen(cmd, stderr=subprocess.DEVNULL, **kwargs)
        write_pid(cfg["name"], "engine", proc.pid)
        ok("Engine started (PID %d)" % proc.pid)
        return proc
    return None


def start_standalone_plugins(cfg):
    """Spawn standalone plugins — inside screen if available."""
    procs = {}
    for pname, settings in cfg.get("plugins", {}).items():
        if isinstance(settings, dict) and not settings.get("enabled", True):
            continue
        script = BASE / "plugins" / pname / ("%s.py" % pname)
        if not script.exists():
            continue
        print("  [%s] Starting..." % pname)
        cmd = [sys.executable, str(script)]
        rtvcfg = mbii_dir(cfg) / ("%s-rtvrtm.cfg" % cfg["name"])
        if rtvcfg.exists():
            cmd += ["-c", str(rtvcfg)]
        # Launch inside the engine's screen session if it exists
        screen_name = "mb2_%s" % cfg["name"]
        if not IS_WINDOWS and _engine_exists(cfg["name"]):
            cmd_str = " ".join(cmd)
            logfile = mbii_dir(cfg) / ("%s-rtvrtm.log" % cfg["name"])
            cmd_str = "%s > %s 2>&1" % (cmd_str, logfile)
            subprocess.Popen(["screen", "-S", screen_name, "-X", "screen", "sh", "-c", cmd_str],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            write_pid(cfg["name"], pname, 1)
            print("  [%s] Started in screen: %s" % (pname, screen_name))
        else:
            proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            write_pid(cfg["name"], pname, proc.pid)
            print("  [%s] Started (PID %d)" % (pname, proc.pid))
            procs[pname] = proc
    return procs


def stop_processes(name):
    for pid_file in PID_DIR.glob("%s_*.pid" % name):
        label = pid_file.stem.replace(name + "_", "")
        pid = read_pid(name, label)
        if label == "engine" and pid == 1:
            # Running under screen — kill screen session
            if _engine_alive(name):
                _engine_kill(name)
                print("  Stopped engine (screen: mb2_%s)" % name)
            remove_pid(name, label)
        elif pid and is_pid_alive(pid):
            kill_pid(pid)
            print("  Stopped %s (PID %d)" % (label, pid))
            remove_pid(name, label)
        else:
            print("  %s not running" % label)
    time.sleep(1)


def _init_plugins(cfg, rcon_client):
    """Load native plugins (no standalone script found)."""
    pm = PluginManager()
    pm.set_rcon(rcon_client.send)

    for name, settings in cfg.get("plugins", {}).items():
        if isinstance(settings, dict) and not settings.get("enabled", True):
            continue
        script = BASE / "plugins" / name / ("%s.py" % name)
        if script.exists():
            continue  # standalone, handled elsewhere
        config = settings if isinstance(settings, dict) else {}
        pm.load_from_config({name: config})

    pm.start_all()
    return pm


def cmd_start(name):
    cfg = load_config(name)
    info("[%s] Generating configs..." % name)
    generate_server_cfg(cfg)
    generate_map_files(cfg)
    generate_rtvrtm_cfg(cfg)

    pid = read_pid(name, "engine")
    if pid and pid != 1 and is_pid_alive(pid):
        warn("[%s] Engine already running (PID %d)" % (name, pid))
        return
    if pid == 1 and _engine_alive(name):
        warn("[%s] Engine already running (screen)" % name)
        return

    info("[%s] Launching..." % name)
    engine = start_engine(cfg)

    info("[%s] Waiting for engine..." % name)
    for _ in range(15):
        if _engine_alive(name):
            break
        time.sleep(1)

    # RCON connection for native plugins + log watching
    rcon = RCONClient(cfg["security"]["rcon_password"], port=cfg["server"]["port"])
    rcon.connect()
    pm = _init_plugins(cfg, rcon)

    # Log watcher feeds events to plugins
    log_path = mbii_dir(cfg) / ("%s-games.log" % name)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.touch()  # Create empty log so rtvrtm can find it
    watcher = LogWatcher(str(log_path), pm)
    watcher.start()

    standalone = start_standalone_plugins(cfg)

    # Fork into background so terminal is freed
    if not IS_WINDOWS and not os.environ.get("MBII_FG"):
        pid = os.fork()
        if pid > 0:
            write_pid(name, "manager", pid)
            print("  Manager running as daemon (PID %d)" % pid)
            return
        os.setsid()
        pid2 = os.fork()
        if pid2 > 0:
            os._exit(0)
        # Detach from terminal completely
        sys.stdin.close()
        sys.stdout.close()
        sys.stderr.close()
        devnull = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull, 0)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.close(devnull)

    print("[%s] Watching processes (auto-restart enabled)..." % name)
    if cfg.get("server", {}).get("restart_every_hours"):
        print("[%s] Scheduled restart every %d hours" % (name, cfg["server"]["restart_every_hours"]))

    if not IS_WINDOWS:
        signal.signal(signal.SIGHUP, lambda s, f: None)

    crashes = 0
    max_crashes = 5
    tick = 0
    engine_start = time.time()
    restart_hours = cfg.get("server", {}).get("restart_every_hours", 0)

    try:
        while True:
            tick += 1
            watcher.poll()
            pm.loop_all()

            engine_alive = is_pid_alive(engine.pid) if engine and hasattr(engine, 'pid') else _engine_alive(name)

            for sname, sproc in list(standalone.items()):
                if not is_pid_alive(sproc.pid):
                    sproc.poll()
                    print("  [%s] died, restarting..." % sname)
                    script = BASE / "plugins" / sname / ("%s.py" % sname)
                    cmd = [sys.executable, str(script)]
                    rtvcfg = mbii_dir(cfg) / ("%s-rtvrtm.cfg" % cfg["name"])
                    if rtvcfg.exists():
                        cmd += ["-c", str(rtvcfg)]
                    if _engine_exists(name):
                        cmd_str = " ".join(cmd)
                        logfile = mbii_dir(cfg) / ("%s-rtvrtm.log" % name)
                        cmd_str = "%s > %s 2>&1" % (cmd_str, logfile)
                        subprocess.Popen(["screen", "-S", "mb2_%s" % name, "-X", "screen", "sh", "-c", cmd_str],
                                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        write_pid(name, sname, p.pid)

            # Scheduled restart check
            if engine_alive and restart_hours > 0:
                elapsed = time.time() - engine_start
                if elapsed >= restart_hours * 3600:
                    print("[%s] Scheduled restart after %d hours" % (name, restart_hours))
                    if engine:
                        kill_pid(engine.pid)
                    else:
                        _engine_kill(name)
                    remove_pid(name, "engine")
                    engine_alive = False

            if not engine_alive:
                if engine:
                    engine.poll()
                    code = engine.returncode if engine.returncode is not None else -1
                    is_scheduled = code == -1
                else:
                    code = -1
                    is_scheduled = True
                if is_scheduled:
                    crashes = 0
                    print("[%s] Performing scheduled restart..." % name)
                else:
                    crashes += 1
                    fail("[%s] Engine crashed (exit %d, crash %d/%d)" % (
                        name, code, crashes, max_crashes))
                    if crashes >= max_crashes:
                        print("[%s] Max crashes reached, giving up" % name)
                        break
                print("[%s] Restarting engine in 5s..." % name)
                time.sleep(5)
                engine = start_engine(cfg)
                engine_start = time.time()
                time.sleep(3)
    except KeyboardInterrupt:
        print("\n%s[%s] Shutting down...%s" % (C.YELLOW, name, C.END))
    finally:
        pm.finish_all()
        watcher.stop()
        rcon.disconnect()
        stop_processes(name)
        print("[%s] Stopped" % name)


def cmd_stop(name):
    print("[%s] Stopping..." % name)
    stop_processes(name)
    # Kill manager daemon too
    mpid = read_pid(name, "manager")
    if mpid and is_pid_alive(mpid):
        kill_pid(mpid)
        remove_pid(name, "manager")
    print("[%s] Stopped" % name)


def cmd_restart(name):
    cmd_stop(name)
    time.sleep(2)
    cmd_start(name)


def cmd_status(name):
    cfg = load_config(name)
    print("Instance: %s" % name)
    print("  Port:   %d" % cfg["server"]["port"])
    print("  Engine: %s" % cfg["server"]["engine"])
    for label in ("engine", "rtvrtm"):
        pid = read_pid(name, label)
        if label == "engine" and pid == 1:
            alive = _engine_alive(name)
            status = "%sRUNNING%s" % (C.GREEN, C.END) if alive else "%sSTOPPED%s" % (C.RED, C.END)
            print("  engine: %s (screen)" % status)
        else:
            alive = is_pid_alive(pid)
            status = "%sRUNNING%s" % (C.GREEN, C.END) if alive else "%sSTOPPED%s" % (C.RED, C.END)
            print("  %s: %s (PID %s)" % (label, status, str(pid) if pid else "-"))


def _running_instances():
    """Return list of instance names that have a running engine."""
    result = []
    for f in CONFIG_DIR.glob("*.json"):
        name = f.stem
        pid = read_pid(name, "engine")
        if pid and pid == 1 and _engine_alive(name):
            result.append(name)
        elif is_pid_alive(pid):
            result.append(name)
    return result




    # Restart previously running instances
    if running:
        print("[UPDATE] Restarting instances...")
        for name in running:
            try:
                cfg = load_config(name)
                print("  [%s] Starting..." % name)
                # Just launch engine + plugins without full cmd_start
                generate_server_cfg(cfg)
                generate_map_files(cfg)
                generate_rtvrtm_cfg(cfg)
                eng = start_engine(cfg)
                standalone = start_standalone_plugins(cfg)
                print("  [%s] Started (PID %d)" % (name, eng.pid))
            except Exception as e:
                print("  [%s] Failed to restart: %s" % (name, e))

    print("[UPDATE] Done")


def cmd_list():
    print("Instances:")
    for f in sorted(CONFIG_DIR.glob("*.json")):
        name = f.stem
        pid = read_pid(name, "engine")
        alive = is_pid_alive(pid) or (pid == 1 and _engine_alive(name))
        marker = "%sRUNNING%s" % (C.GREEN, C.END) if alive else "%sSTOPPED%s" % (C.RED, C.END)
        print("  %s [%s]" % (name, marker))


def main():
    if len(sys.argv) < 2:
        print("Usage: manager.py <name> <start|stop|restart|status>")
        print("       manager.py --list")
        print("")
        print("Updates are handled automatically by the updater plugin.")
        sys.exit(1)

    if sys.argv[1] == "--list":
        cmd_list()
        return

    name = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "start"

    actions = {
        "start": cmd_start,
        "stop": cmd_stop,
        "restart": cmd_restart,
        "status": cmd_status,
    }
    fn = actions.get(action)
    if fn:
        fn(name)
    else:
        print("Unknown action: %s" % action)
        sys.exit(1)


if __name__ == "__main__":
    main()
