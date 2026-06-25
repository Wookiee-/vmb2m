"""Example plugin: rotates messages in chat every N seconds."""

from plugins.base import BasePlugin
from plugins import event_types as events


class AutoMessagePlugin(BasePlugin):
    name = "auto_message"
    version = "1.0"

    def on_init(self, api, config):
        self.api = api
        self.messages = config.get("messages", [])
        self.interval = config.get("interval", 300)
        if not self.messages:
            return False
        self._index = 0
        self._timer = 0
        return True

    def on_loop(self):
        self._timer += 1
        if self._timer >= self.interval:
            self._timer = 0
            msg = self.messages[self._index % len(self.messages)]
            self._index += 1
            self.api.say("^2[Server] ^7%s" % msg)

    def on_finish(self):
        self.api = None
