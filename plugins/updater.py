"""Auto-updater plugin. Checks for MBII updates on a schedule (own thread)."""

import os
import subprocess
import threading
import time

from plugins.base import BasePlugin


class UpdaterPlugin(BasePlugin):
    name = "updater"
    version = "1.0"

    def on_init(self, api, config):
        self.check_interval = config.get("check_interval_minutes", 60)
        self.gamedir = config.get("gamedir", os.path.expanduser("~/openjk"))
        self._stop = False

        dotnet_root = os.environ.get("DOTNET_ROOT", os.path.expanduser("~/.dotnet"))
        dotnet_path = os.path.join(dotnet_root, "dotnet")
        if os.path.exists(dotnet_path):
            self.dotnet = dotnet_path
        else:
            try:
                subprocess.run(["which", "dotnet"], capture_output=True, check=True)
                self.dotnet = "dotnet"
            except subprocess.CalledProcessError:
                print("  [updater] .NET SDK not found — disabled")
                return False

        self.dll = os.path.join(self.gamedir, "MBII_CommandLine_Update_XPlatform.dll")
        if not os.path.exists(self.dll):
            fallback = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                    "updater", "MBII_CommandLine_Update_XPlatform.dll")
            if os.path.exists(fallback):
                self.dll = fallback
            else:
                print("  [updater] MBII updater DLL not found — disabled")
                return False

        print("  [updater] Active — checking every %d min" % self.check_interval)
        return True

    def on_start(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()
        return True

    def _run(self):
        time.sleep(30)  # Initial delay
        while not self._stop:
            self._check_and_update()
            for _ in range(self.check_interval * 60):
                if self._stop:
                    return
                time.sleep(1)

    def _check_and_update(self):
        try:
            result = subprocess.run(
                [self.dotnet, self.dll, "-c", "-path", self.gamedir],
                cwd=os.path.dirname(self.dll),
                capture_output=True, timeout=180,
            )
            out = result.stdout.decode(errors="replace").strip()
            count = 0
            for line in out.split("\n"):
                try:
                    count = int(line.strip())
                    break
                except ValueError:
                    continue
            if count <= 1:
                return
            print("  [updater] %d updates available" % count)
            for attempt in range(1, 11):
                try:
                    result = subprocess.run(
                        [self.dotnet, self.dll, "-path", self.gamedir],
                        cwd=os.path.dirname(self.dll),
                        capture_output=True, timeout=180,
                    )
                    if result.returncode == 0:
                        print("  [updater] Update successful")
                        self._patch_engine_lib()
                        return
                    time.sleep(min(30, 2 ** attempt))
                except subprocess.TimeoutExpired:
                    pass
        except Exception as e:
            print("  [updater] Error: %s" % e)

    def _patch_engine_lib(self):
        mbii = os.path.join(self.gamedir, "MBII")
        old = os.path.join(mbii, "jampgamei386.so")
        nopp = os.path.join(mbii, "jampgamei386.nopp.so")
        if os.path.exists(nopp) and os.path.exists(old):
            backup = os.path.join(mbii, "jampgamei386.jamp.so")
            try:
                if not os.path.exists(backup):
                    os.rename(old, backup)
                import shutil
                shutil.copy2(nopp, old)
            except Exception:
                pass

    def on_finish(self):
        self._stop = True
