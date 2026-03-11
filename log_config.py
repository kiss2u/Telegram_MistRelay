import os
import time
import logging
import logging.handlers
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db', 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'mistrelay.log')

# 单个日志文件最大 10MB，保留最近 5 个备份
MAX_BYTES = 10 * 1024 * 1024
BACKUP_COUNT = 5

# 日志保留时长：24 小时
LOG_MAX_AGE_SECONDS = 24 * 3600

_initialized = False


def cleanup_old_logs():
    """删除超过 24 小时的日志文件。"""
    if not os.path.isdir(LOG_DIR):
        return
    now = time.time()
    for name in os.listdir(LOG_DIR):
        path = os.path.join(LOG_DIR, name)
        if os.path.isfile(path) and name.startswith('mistrelay'):
            if now - os.path.getmtime(path) > LOG_MAX_AGE_SECONDS:
                try:
                    os.remove(path)
                except Exception:
                    pass


def setup_logging(level=logging.INFO):
    """
    初始化全局日志系统：控制台 + 文件双输出。
    文件日志使用 RotatingFileHandler 自动轮转。
    此函数应在程序最早期调用（在任何 getLogger 之前最好）。
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    os.makedirs(LOG_DIR, exist_ok=True)
    cleanup_old_logs()

    file_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-7s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8',
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)


def get_log_files():
    """返回所有日志文件信息列表，按修改时间降序。"""
    if not os.path.isdir(LOG_DIR):
        return []

    files = []
    for name in os.listdir(LOG_DIR):
        path = os.path.join(LOG_DIR, name)
        if os.path.isfile(path) and name.startswith('mistrelay'):
            stat = os.stat(path)
            files.append({
                'name': name,
                'path': path,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            })

    files.sort(key=lambda f: f['modified'], reverse=True)
    return files


def read_log_lines(filename=None, tail=200, level_filter=None, keyword=None):
    """
    读取日志内容。

    :param filename: 指定日志文件名，为 None 时读取当前日志文件
    :param tail: 返回最后 N 行
    :param level_filter: 按级别过滤（如 "ERROR", "WARNING"）
    :param keyword: 关键词搜索
    :return: 日志行列表
    """
    if filename:
        path = os.path.join(LOG_DIR, os.path.basename(filename))
    else:
        path = LOG_FILE

    if not os.path.isfile(path):
        return []

    lines = []
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.rstrip('\n')
                if level_filter and f'| {level_filter.upper()}' not in line.upper():
                    continue
                if keyword and keyword.lower() not in line.lower():
                    continue
                lines.append(line)
    except Exception:
        return []

    if tail and tail > 0:
        lines = lines[-tail:]

    return lines
