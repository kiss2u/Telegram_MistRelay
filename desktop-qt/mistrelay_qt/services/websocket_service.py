from __future__ import annotations

import asyncio
import json
import threading
from typing import Any

import websockets
from PySide6.QtCore import QObject, Signal

from .config_service import ConfigService


class WebsocketService(QObject):
    connectionStateChanged = Signal(str)
    statusReceived = Signal("QVariantMap")
    errorRaised = Signal(str)

    def __init__(self, config_service: ConfigService) -> None:
        super().__init__()
        self._config_service = config_service
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._expected_sequence: int | None = None
        self._buffer: dict[int, dict[str, Any]] = {}

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        if not self._config_service.config.server_base_url:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        try:
            asyncio.run(self._listen())
        except RuntimeError as exc:
            self.errorRaised.emit(str(exc))

    async def _listen(self) -> None:
        while not self._stop_event.is_set():
            url = self._build_url()
            headers = {}
            token = self._config_service.config.auth_token.strip()
            if token:
                headers["Authorization"] = f"Bearer {token}"

            self.connectionStateChanged.emit("connecting")
            try:
                async with websockets.connect(
                    url,
                    additional_headers=headers or None,
                    ping_interval=20,
                    ping_timeout=20,
                ) as socket:
                    self.connectionStateChanged.emit("connected")
                    self._expected_sequence = None
                    self._buffer.clear()

                    async for raw_message in socket:
                        if self._stop_event.is_set():
                            break
                        payload = json.loads(raw_message)
                        self._accept_message(payload)
            except Exception as exc:  # pragma: no cover - network dependent
                self.connectionStateChanged.emit("disconnected")
                self.errorRaised.emit(str(exc))
                await asyncio.sleep(3)

        self.connectionStateChanged.emit("disconnected")

    def _build_url(self) -> str:
        base = self._config_service.config.server_base_url.rstrip("/")
        if base.startswith("https://"):
            return f"wss://{base.removeprefix('https://')}/api/ws/status"
        if base.startswith("http://"):
            return f"ws://{base.removeprefix('http://')}/api/ws/status"
        return f"wss://{base}/api/ws/status"

    def _accept_message(self, payload: dict[str, Any]) -> None:
        sequence = payload.get("sequence", payload.get("seq"))
        if not isinstance(sequence, int):
            self.statusReceived.emit(payload)
            return

        if self._expected_sequence is None:
            self._expected_sequence = sequence

        if sequence == self._expected_sequence:
            self.statusReceived.emit(payload)
            self._expected_sequence += 1
            self._flush_buffer()
            return

        if sequence > self._expected_sequence:
            self._buffer[sequence] = payload

    def _flush_buffer(self) -> None:
        while self._expected_sequence in self._buffer:
            payload = self._buffer.pop(self._expected_sequence)
            self.statusReceived.emit(payload)
            self._expected_sequence += 1
