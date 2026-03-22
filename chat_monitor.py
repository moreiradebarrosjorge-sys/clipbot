import asyncio
import websockets
import time
import re
from collections import deque
from config import (
    SPIKE_THRESHOLD, SPIKE_WINDOW_SEC, SPIKE_KEYWORDS,
    TWITCH_ACCESS_TOKEN, TWITCH_CLIENT_ID
)


class ChatMonitor:
    def __init__(self, streamer: dict, on_spike):
        self.name       = streamer["name"]
        self.on_spike   = on_spike
        self.timestamps = deque()
        self.running    = False
        self.msg_count  = 0

    async def start(self):
        self.running = True
        while self.running:
            try:
                await self._connect_twitch()
            except Exception as e:
                print(f"[{self.name}] Connexion perdue : {e}. Reconnexion dans 10s...")
                await asyncio.sleep(10)

    def stop(self):
        self.running = False

    async def _connect_twitch(self):
        uri = "wss://irc-ws.chat.twitch.tv:443"
        async with websockets.connect(uri) as ws:
            await ws.send(f"PASS oauth:{TWITCH_ACCESS_TOKEN}")
            await ws.send(f"NICK {TWITCH_CLIENT_ID}")
            await ws.send(f"JOIN #{self.name}")
            print(f"[{self.name}] Connecté au chat Twitch")

            async for raw in ws:
                if not self.running:
                    break
                if raw.startswith("PING"):
                    await ws.send("PONG :tmi.twitch.tv")
                    continue
                if "PRIVMSG" in raw:
                    message = self._parse_twitch_message(raw)
                    self.msg_count += 1
                    if self.msg_count % 100 == 0:
                        print(f"[{self.name}] {self.msg_count} messages reçus au total")
                    self._register_message(message)

    def _parse_twitch_message(self, raw: str) -> str:
        match = re.search(r"PRIVMSG #\w+ :(.+)", raw)
        return match.group(1).strip() if match else ""

    def _register_message(self, message: str):
        now = time.time()
        self.timestamps.append(now)

        cutoff = now - SPIKE_WINDOW_SEC
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()

        rate = len(self.timestamps) / SPIKE_WINDOW_SEC
        keyword_boost = self._count_keywords(message)

        if rate >= SPIKE_THRESHOLD or (rate >= SPIKE_THRESHOLD * 0.7 and keyword_boost > 0):
            print(f"[{self.name}] SPIKE DETECTE — {rate:.0f} msg/s — déclenchement clip")
            asyncio.create_task(self.on_spike(self.name, rate))
            self.timestamps.clear()

    def _count_keywords(self, message: str) -> int:
        msg_lower = message.lower()
        return sum(1 for kw in SPIKE_KEYWORDS if kw in msg_lower)
