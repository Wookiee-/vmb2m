"""Rotates messages in chat every N seconds."""

import time

from plugins.base import BasePlugin


class AutoMessagePlugin(BasePlugin):
    name = "automessage"
    version = "1.0"

    def on_init(self, api, config):
        self.api = api
        self.messages = config.get("messages", [])
        self.interval = config.get("interval", 300)
        if not self.messages:
            return False
        self._index = 0
        self._last = time.time()
        print("  [automessage] Active — %d messages every %ds" % (len(self.messages), self.interval))
        return True

    def on_loop(self):
        now = time.time()
        if now - self._last >= self.interval:
            self._last = now
            msg = self.messages[self._index % len(self.messages)]
            self._index += 1
            self.api.say("^2[Server] ^7%s" % msg)

    def on_finish(self):
        self.api = None
