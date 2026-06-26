"""Auto-updater plugin. Checks for MBII updates on a schedule."""

import os
import subprocess
import threading
import time

from plugins.base import BasePlugin


class UpdaterPlugin(BasePlugin):
    name = "updater"
    version = "1.0"

    def on_init(self, api, config):
        self.api = api
        self.check_interval = config.get("check_interval_minutes", 60)
        self.gamedir = config.get("gamedir", os.path.expanduser("~/openjk"))
        self._last_check = 0
        self._checking = False

        # Find dotnet
        self.dotnet = None
        dotnet_root = os.environ.get("DOTNET_ROOT", os.path.expanduser("~/.dotnet"))
        dotnet_path = os.path.join(dotnet_root, "dotnet")
        if os.path.exists(dotnet_path):
            self.dotnet = dotnet_path
            os.environ["DOTNET_ROOT"] = dotnet_root
        else:
            try:
                subprocess.run(["which", "dotnet"], capture_output=True, check=True)
                self.dotnet = "dotnet"
            except subprocess.CalledProcessError:
                pass

        if not self.dotnet:
            print("  [updater] .NET SDK not found — disabled")
            return False

        # Find updater DLL
        self.updater_dll = os.path.join(self.gamedir, "MBII_CommandLine_Update_XPlatform.dll")
        if not os.path.exists(self.updater_dll):
            fallback = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                    "updater", "MBII_CommandLine_Update_XPlatform.dll")
            if os.path.exists(fallback):
                self.updater_dll = fallback
            else:
                print("  [updater] MBII updater DLL not found — disabled")
                return False

        print("  [updater] Active — checking every %d min" % self.check_interval)
        return True

    def on_loop(self):
        if self.check_interval <= 0:
            return
        if time.time() - self._last_check < self.check_interval * 60:
            return
        if self._checking:
            return
        self._last_check = time.time()
        self._checking = True
        threading.Thread(target=self._check_and_update, daemon=True).start()

    def _check_and_update(self):
        try:
            result = subprocess.run(
                [self.dotnet, self.updater_dll, "-c", "-path", self.gamedir],
                cwd=os.path.dirname(self.updater_dll),
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
            print("  [updater] Applying update...")
            for attempt in range(1, 11):
                try:
                    result = subprocess.run(
                        [self.dotnet, self.updater_dll, "-path", self.gamedir],
                        cwd=os.path.dirname(self.updater_dll),
                        capture_output=True, timeout=180,
                    )
                    if result.returncode == 0:
                        print("  [updater] Update successful (attempt %d)" % attempt)
                        self._patch_engine_lib()
                        print("  [updater] Update complete")
                        return
                    print("  [updater] Attempt %d failed" % attempt)
                    time.sleep(min(30, 2 ** attempt))
                except subprocess.TimeoutExpired:
                    print("  [updater] Attempt %d timed out" % attempt)

            print("  [updater] Update failed after 10 attempts")
        except Exception as e:
            print("  [updater] Check error: %s" % e)
        finally:
            self._checking = False

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
                print("  [updater] Patched engine library (nopp -> so)")
            except Exception as e:
                print("  [updater] Failed to patch engine lib: %s" % e)
