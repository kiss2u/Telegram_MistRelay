# This file is a part of TG-FileStreamBot
# Coding : Jyothis Jayanth [@EverythingSuckz]

import os
import os.path
import re
import time
import threading
from ..vars import Var
import logging
from pyrogram import Client

logger = logging.getLogger("bot")

sessions_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
if Var.USE_SESSION_FILE:
    logger.info("Using session files")
    logger.info("Session folder path: {}".format(sessions_dir))
    if not os.path.isdir(sessions_dir):
        os.makedirs(sessions_dir)

# 使用Python模块路径而不是文件系统路径（在Docker中更可靠）
StreamBot = Client(
    name="WebStreamer",
    api_id=Var.API_ID,
    api_hash=Var.API_HASH,
    workdir=sessions_dir if Var.USE_SESSION_FILE else "WebStreamer",
    plugins={"root": "WebStreamer.bot.plugins"},
    bot_token=Var.BOT_TOKEN,
    sleep_threshold=Var.SLEEP_THRESHOLD,
    workers=Var.WORKERS,
    in_memory=not Var.USE_SESSION_FILE,
)

multi_clients = {}
work_loads = {}
# 跟踪哪些客户端可以访问 BIN_CHANNEL
channel_accessible_clients = set()
bot_runtime = {}

_scheduler_lock = threading.Lock()
_scheduler_cursor = -1


def _ensure_bot_runtime(index: int) -> dict:
    state = bot_runtime.get(index)
    if state is None:
        state = {
            "cooldown_until": 0.0,
            "cooldown_reason": "",
            "failure_streak": 0,
            "success_count": 0,
            "failure_count": 0,
            "request_count": 0,
            "bytes_served": 0,
            "throughput_bps": 0.0,
            "last_byte_at": 0.0,
            "last_selected_at": 0.0,
            "last_error": "",
        }
        bot_runtime[index] = state
    return state


def register_bot_client(index: int) -> None:
    with _scheduler_lock:
        work_loads.setdefault(index, 0)
        _ensure_bot_runtime(index)


def _channel_candidate_indices(prefer_channel: bool = True) -> list[int]:
    if prefer_channel:
        indices = [idx for idx in channel_accessible_clients if idx in multi_clients]
        if indices:
            return sorted(indices)
    return sorted(idx for idx in multi_clients.keys())


def _parse_cooldown_seconds(error: Exception | str | None, failure_streak: int) -> int:
    if error is None:
        return min(30, 3 + failure_streak * 3)

    if hasattr(error, "value"):
        try:
            return max(5, int(error.value))
        except Exception:
            pass

    text = str(error)
    lowered = text.lower()

    if "flood" in lowered:
        match = re.search(r"(\d+)\s*second", lowered)
        if match:
            return max(5, int(match.group(1)))
        return 60

    if any(marker in lowered for marker in [
        "connection lost",
        "connection closed",
        "broken pipe",
        "timeout",
        "timed out",
        "network",
        "reset by peer",
    ]):
        return min(20, 2 + failure_streak * 2)

    return min(45, 5 + failure_streak * 4)


def get_available_channel_bot_count() -> int:
    indices = _channel_candidate_indices(prefer_channel=True)
    return max(1, len(indices))


def get_bot_runtime_snapshot() -> dict:
    now = time.time()
    with _scheduler_lock:
        snapshot = {}
        for idx in sorted(multi_clients.keys()):
            state = _ensure_bot_runtime(idx)
            snapshot[idx] = {
                "active_requests": work_loads.get(idx, 0),
                "cooldown_remaining": max(0.0, state["cooldown_until"] - now),
                "cooldown_reason": state["cooldown_reason"],
                "failure_streak": state["failure_streak"],
                "success_count": state["success_count"],
                "failure_count": state["failure_count"],
                "request_count": state["request_count"],
                "bytes_served": state["bytes_served"],
                "throughput_bps": state["throughput_bps"],
                "last_selected_at": state["last_selected_at"],
                "last_error": state["last_error"],
            }
        return snapshot


def acquire_bot_slot(index: int) -> None:
    now = time.time()
    with _scheduler_lock:
        work_loads[index] = work_loads.get(index, 0) + 1
        state = _ensure_bot_runtime(index)
        state["request_count"] += 1
        state["last_selected_at"] = now


def release_bot_slot(index: int) -> None:
    with _scheduler_lock:
        if index in work_loads and work_loads[index] > 0:
            work_loads[index] -= 1


def record_bot_bytes(index: int, byte_count: int) -> None:
    if byte_count <= 0:
        return

    now = time.time()
    with _scheduler_lock:
        state = _ensure_bot_runtime(index)
        state["bytes_served"] += byte_count
        last_byte_at = state["last_byte_at"]
        if last_byte_at > 0 and now > last_byte_at:
            instant_bps = byte_count / max(now - last_byte_at, 1e-3)
            if state["throughput_bps"] <= 0:
                state["throughput_bps"] = instant_bps
            else:
                state["throughput_bps"] = state["throughput_bps"] * 0.7 + instant_bps * 0.3
        state["last_byte_at"] = now


def mark_bot_success(index: int) -> None:
    with _scheduler_lock:
        state = _ensure_bot_runtime(index)
        state["success_count"] += 1
        state["failure_streak"] = 0
        state["cooldown_until"] = 0.0
        state["cooldown_reason"] = ""
        state["last_error"] = ""


def mark_bot_failure(index: int, error: Exception | str | None = None) -> None:
    now = time.time()
    with _scheduler_lock:
        state = _ensure_bot_runtime(index)
        state["failure_count"] += 1
        state["failure_streak"] += 1
        state["last_error"] = str(error or "")
        cooldown_seconds = _parse_cooldown_seconds(error, state["failure_streak"])
        state["cooldown_until"] = max(state["cooldown_until"], now + cooldown_seconds)
        state["cooldown_reason"] = str(error or f"cooldown:{cooldown_seconds}s")


def select_stream_bot(
    *,
    exclude_indices: set[int] | None = None,
    prefer_channel: bool = True,
) -> int | None:
    global _scheduler_cursor

    excluded = set(exclude_indices or ())
    now = time.time()

    with _scheduler_lock:
        candidates = [idx for idx in _channel_candidate_indices(prefer_channel) if idx not in excluded]
        if not candidates:
            return None

        ready = [
            idx for idx in candidates
            if _ensure_bot_runtime(idx)["cooldown_until"] <= now
        ]
        if not ready:
            return None
        pool = ready

        ordered = sorted(pool)
        if ordered:
            if _scheduler_cursor not in ordered:
                rotation_start = 0
            else:
                rotation_start = (ordered.index(_scheduler_cursor) + 1) % len(ordered)
            rotated = ordered[rotation_start:] + ordered[:rotation_start]
        else:
            rotated = []

        position_map = {idx: pos for pos, idx in enumerate(rotated)}

        def score(idx: int) -> tuple[float, int, int]:
            state = _ensure_bot_runtime(idx)
            cooldown_remaining = max(0.0, state["cooldown_until"] - now)
            active_load = work_loads.get(idx, 0)
            failure_penalty = min(state["failure_streak"], 5) * 0.5
            cooldown_penalty = cooldown_remaining if not ready else 0.0
            return (
                active_load + failure_penalty + cooldown_penalty,
                position_map.get(idx, 0),
                idx,
            )

        selected = min(pool, key=score)
        _scheduler_cursor = selected
        _ensure_bot_runtime(selected)["last_selected_at"] = now
        return selected
