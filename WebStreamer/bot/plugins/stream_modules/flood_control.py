# This file is a part of TG-FileStreamBot
# Coding : Jyothis Jayanth [@EverythingSuckz]

"""
限流控制模块
管理 Telegram API 限流状态，实现智能队列暂停和恢复
"""

import logging
import time
import asyncio
from WebStreamer.vars import Var

logger = logging.getLogger(__name__)

# 限流状态管理
# 用于跟踪 Telegram 限流状态,实现智能队列暂停和恢复
flood_wait_status = {
    'is_flood_waiting': False,  # 是否处于限流状态
    'flood_wait_until': 0,  # 限流结束时间戳
    'flood_wait_seconds': 0,  # 限流等待秒数
    'notification_message_id': None,  # 限流通知消息ID
    'notification_chat_id': None  # 限流通知发送的频道ID
}
flood_wait_lock = asyncio.Lock() if asyncio else None  # 限流状态锁


def extract_flood_wait_seconds(error: Exception) -> int:
    """从 FloodWait 错误中提取等待秒数"""
    try:
        if hasattr(error, 'value'):
            return int(error.value)
        error_str = str(error)
        import re
        match = re.search(r'(\d+)\s*second', error_str, re.IGNORECASE)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return 300


async def handle_flood_wait_start(error: Exception):
    """处理限流开始"""
    global flood_wait_status, flood_wait_lock
    wait_seconds = extract_flood_wait_seconds(error)
    if wait_seconds <= 0:
        wait_seconds = 300
    async with flood_wait_lock:
        flood_wait_status['is_flood_waiting'] = True
        flood_wait_status['flood_wait_seconds'] = wait_seconds
        flood_wait_status['flood_wait_until'] = time.time() + wait_seconds
    logger.warning(f"检测到 Telegram 限流,等待 {wait_seconds} 秒 ({wait_seconds // 60} 分钟)")
    await send_flood_wait_notification(wait_seconds)


async def send_flood_wait_notification(wait_seconds: int):
    """使用备用 bot 向频道发送限流通知"""
    global flood_wait_status
    if not Var.BIN_CHANNEL:
        logger.warning("BIN_CHANNEL 未配置,无法发送限流通知")
        return
    from WebStreamer.bot import multi_clients, work_loads
    available_bots = [(idx, client) for idx, client in multi_clients.items() if idx != 0]
    if not available_bots:
        logger.warning("没有可用的备用 bot 发送限流通知")
        return
    best_bot_idx = min(available_bots, key=lambda x: work_loads.get(x[0], 0))[0]
    backup_bot = multi_clients[best_bot_idx]
    try:
        import datetime
        end_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=wait_seconds)
        end_time_str = end_time.strftime('%H:%M:%S UTC')
        notification_text = (
            f"⚠️ **Telegram 限流通知**\\n\\n"
            f"🚫 主 bot 已被 Telegram 限流\\n"
            f"⏰ 限流时长: {wait_seconds} 秒 ({wait_seconds // 60} 分钟)\\n"
            f"🕐 预计恢复时间: {end_time_str}\\n\\n"
            f"📋 **队列状态:**\\n"
            f"• 所有新消息已进入等待队列\\n"
            f"• 限流结束后将自动恢复处理\\n"
            f"• 请耐心等待,无需重复发送\\n\\n"
            f"_此消息将在限流结束后自动删除_"
        )
        msg = await backup_bot.send_message(chat_id=Var.BIN_CHANNEL, text=notification_text)
        async with flood_wait_lock:
            flood_wait_status['notification_message_id'] = msg.id
            flood_wait_status['notification_chat_id'] = Var.BIN_CHANNEL
        logger.info(f"已使用备用 bot {best_bot_idx} 发送限流通知到频道")
    except Exception as e:
        logger.error(f"发送限流通知失败: {e}", exc_info=True)


async def handle_flood_wait_end():
    """处理限流结束,恢复队列处理"""
    global flood_wait_status, flood_wait_lock
    logger.info("Telegram 限流已结束,恢复队列处理")
    await delete_flood_wait_notification()
    async with flood_wait_lock:
        flood_wait_status['is_flood_waiting'] = False
        flood_wait_status['flood_wait_until'] = 0
        flood_wait_status['flood_wait_seconds'] = 0
        flood_wait_status['notification_message_id'] = None
        flood_wait_status['notification_chat_id'] = None


async def delete_flood_wait_notification():
    """删除限流通知消息"""
    global flood_wait_status
    async with flood_wait_lock:
        msg_id = flood_wait_status['notification_message_id']
        chat_id = flood_wait_status['notification_chat_id']
    if not msg_id or not chat_id:
        return
    from WebStreamer.bot import multi_clients
    for idx, client in multi_clients.items():
        try:
            await client.delete_messages(chat_id=chat_id, message_ids=[msg_id])
            logger.info(f"已删除限流通知消息 (使用 bot {idx})")
            return
        except Exception as e:
            logger.debug(f"使用 bot {idx} 删除通知失败: {e}")
    logger.warning("无法删除限流通知消息")
