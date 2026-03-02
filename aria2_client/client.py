"""
Aria2 WebSocket客户端核心模块
"""
import logging
import asyncio
import base64
import json
import uuid
from typing import List, Dict, Any, Optional

import aiohttp
import websockets

from configer import get_config_value

from .download_handler import DownloadHandler
from .upload_handler import UploadHandler


logger = logging.getLogger(__name__)

class AsyncAria2Client:
    """Aria2异步WebSocket客户端"""
    
    def __init__(self, rpc_secret, ws_url, bot=None):
        """
        初始化Aria2客户端
        
        Args:
            rpc_secret: RPC密钥
            ws_url: WebSocket URL
            bot: Telegram bot实例(可选)
        """
        self.rpc_secret = rpc_secret
        self.ws_url = ws_url
        self.websocket = None
        self.reconnect = True
        self.bot = bot
        self.progress_cache = {}
        self.download_messages = {}  # 存储每个下载任务的消息对象
        self.completed_gids = set()  # 记录已完成的GID，防止重复处理
        
        # 轮询相关
        self.polling_task = None  # 轮询任务
        self.is_polling = False   # 轮询状态标志
        
        # 初始化处理器
        self.upload_handler = UploadHandler(bot, self.progress_cache)
        self.download_handler = DownloadHandler(
            bot, 
            self.download_messages, 
            self.completed_gids,
            self.upload_handler,
            self  # 传递客户端实例，用于移除任务
        )

    async def connect(self):
        """连接到Aria2 WebSocket服务器"""
        try:
            # 从RPC_URL中提取主机和端口
            url_parts = self.ws_url.split('/')
            ws_protocol = url_parts[0].split(':')[0]  # 获取ws或wss
            host_port = url_parts[2]  # 跳过ws://
            path = '/'.join(url_parts[3:])
            
            # 如果主机名不是localhost或IP地址，则在Docker环境中使用localhost
            if ':' in host_port:
                host, port = host_port.split(':')
                if not (host == 'localhost' or host == '127.0.0.1' or all(c.isdigit() or c == '.' for c in host)):
                    # 在Docker环境中，使用localhost
                    host = 'localhost'
                host_port = f"{host}:{port}"
            
            # 重新构建完整URL
            full_ws_url = f"{ws_protocol}://{host_port}/{path}"
            
            logger.info(f"连接到aria2 WebSocket: {full_ws_url}")
            self.websocket = await websockets.connect(full_ws_url, ping_interval=30)
            logger.info("WebSocket连接成功")
            asyncio.ensure_future(self.listen())
            
            # 启动轮询任务
            await self.start_polling()
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}", exc_info=True)
            await self.re_connect()

    async def listen(self):
        """监听WebSocket消息"""
        try:
            async for message in self.websocket:
                result = json.loads(message)
                if 'id' in result and result['id'] is None:
                    continue
                logger.info(f'rec message:{message}')
                if 'error' in result:
                    err_msg = result['error']['message']
                    err_code = result['error']['code']
                elif 'method' in result:
                    method_name = result['method']
                    if method_name == 'aria2.onDownloadStart':
                        await self.download_handler.on_download_start(result, self.tell_status)
                    elif method_name == 'aria2.onDownloadComplete':
                        await self.download_handler.on_download_complete(result, self.tell_status)
                    elif method_name == 'aria2.onDownloadError':
                        await self.download_handler.on_download_error(result, self.tell_status)
                    elif method_name == 'aria2.onDownloadPause':
                        await self.download_handler.on_download_pause(result, self.tell_status)
        except websockets.exceptions.ConnectionClosedError:
            logger.info("WebSocket连接已关闭")
            # 停止轮询
            await self.stop_polling()
            await self.re_connect()

    def parse_json_to_str(self, method, params):
        """将RPC方法和参数转换为JSON字符串"""
        params_ = self.get_rpc_body(method, params)
        return json.dumps(params_)

    def get_rpc_body(self, method, params=[]):
        """构建RPC请求体"""
        params_ = {
            'jsonrpc': '2.0',
            'id': str(uuid.uuid4()),
            'method': method,
            'params': [f'token:{self.rpc_secret}'] + params
        }
        return params_

    async def add_uri(self, uris: List[str], options: Dict[str, Any] = None):
        """
        添加URI下载任务
        
        Args:
            uris: URI列表
            options: 下载选项
            
        Returns:
            dict: RPC响应结果
        """
        params = [uris]
        if options:
            params.append(options)

        rpc_body = self.get_rpc_body('aria2.addUri', params)
        logger.info(rpc_body)
        result = await self.post_body(rpc_body)
        
        return result

    async def add_torrent(self, path, options=None, position: int = None):
        """
        添加种子下载任务
        
        Args:
            path: 种子文件路径
            options: 下载选项
            position: 队列位置
            
        Returns:
            dict: RPC响应结果
        """
        with open(path, "rb") as file:
            # 读取文件内容
            file_content = file.read()
            base64_content = str(base64.b64encode(file_content), "utf-8")
        params = [
            base64_content
        ]
        if options:
            params.append(options)
        if position is not None:
            params.append(position)
        else:
            params.append([999])

        rpc_body = self.get_rpc_body('aria2.addTorrent', params)
        return await self.post_body(rpc_body)

    async def tell_status(self, gid):
        """
        获取任务状态
        
        Args:
            gid: 任务GID
            
        Returns:
            dict: 任务状态信息
        """
        params = [gid]
        rpc_body = self.get_rpc_body('aria2.tellStatus', params)
        data = await self.post_body(rpc_body)
        return data['result']

    async def post_body(self, rpc_body):
        """
        发送RPC请求
        
        Args:
            rpc_body: RPC请求体
            
        Returns:
            dict: RPC响应
        """
        # 动态从数据库读取RPC_URL配置
        rpc_url = get_config_value('RPC_URL', 'localhost:6800/jsonrpc')
        # 从RPC_URL中提取主机和端口
        url_parts = rpc_url.split('/')
        host_port = url_parts[0]
        path = '/'.join(url_parts[1:])
        
        # 如果主机名不是localhost或IP地址，则在Docker环境中使用localhost
        if ':' in host_port:
            host, port = host_port.split(':')
            if not (host == 'localhost' or host == '127.0.0.1' or all(c.isdigit() or c == '.' for c in host)):
                # 在Docker环境中，使用localhost
                host = 'localhost'
            host_port = f"{host}:{port}"
        
        # 重新构建完整URL
        full_url = f"http://{host_port}/{path}"

        async with aiohttp.ClientSession() as session:
            async with session.post(full_url, json=rpc_body) as response:
                return await response.json()

    async def re_connect(self):
        """重新连接到WebSocket服务器"""
        if self.reconnect:
            logger.info("等待5秒后尝试重新连接...")
            await asyncio.sleep(5)
            await self.connect()
        else:
            logger.info("已禁用重新连接功能")

    async def tell_stopped(self, offset: int, num: int):
        """获取已停止的任务列表"""
        params = [
            offset, num
        ]
        rpc_body = self.get_rpc_body('aria2.tellStopped', params)
        data = await self.post_body(rpc_body)
        return data['result']

    async def tell_waiting(self, offset: int, num: int):
        """获取等待中的任务列表"""
        params = [
            offset, num
        ]
        rpc_body = self.get_rpc_body('aria2.tellWaiting', params)
        data = await self.post_body(rpc_body)
        return data['result']

    async def tell_active(self):
        """获取活动任务列表"""
        params = []
        rpc_body = self.get_rpc_body('aria2.tellActive', params)
        data = await self.post_body(rpc_body)
        return data['result']

    async def pause(self, gid: str):
        """暂停任务"""
        params = [gid]
        jsonreq = self.parse_json_to_str('aria2.pause', params)
        logger.info(jsonreq)
        await self.websocket.send(jsonreq)

    async def unpause(self, gid: str):
        """恢复任务"""
        params = [gid]
        jsonreq = self.parse_json_to_str('aria2.unpause', params)
        logger.info(jsonreq)
        await self.websocket.send(jsonreq)

    async def remove(self, gid: str):
        """移除任务"""
        params = [gid]
        rpc_body = self.get_rpc_body('aria2.remove', params)
        data = await self.post_body(rpc_body)
        return data

    async def remove_download_result(self, gid: str):
        """移除下载结果"""
        params = [gid]
        jsonreq = self.parse_json_to_str('aria2.removeDownloadResult', params)
        logger.info(jsonreq)
        await self.websocket.send(jsonreq)

    async def change_global_option(self, params):
        """修改全局选项"""
        rpc_body = self.get_rpc_body('aria2.changeGlobalOption', params)
        return await self.post_body(rpc_body)

    async def get_global_option(self):
        """获取全局选项"""
        rpc_body = self.get_rpc_body('aria2.getGlobalOption')
        data = await self.post_body(rpc_body)
        return data['result']

    async def start_polling(self):
        """启动轮询任务"""
        if self.is_polling:
            logger.info("[轮询] 轮询任务已在运行")
            return
        
        self.is_polling = True
        self.polling_task = asyncio.create_task(self.poll_active_downloads())
        logger.info("[轮询] 已启动轮询任务")
    
    async def stop_polling(self):
        """停止轮询任务"""
        self.is_polling = False
        if self.polling_task:
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass
            self.polling_task = None
        logger.info("[轮询] 已停止轮询任务")
    
    async def poll_active_downloads(self):
        """
        轮询活动下载任务的核心逻辑
        定期查询aria2活动任务并同步状态
        """
        from .constants import POLL_INTERVAL, IDLE_CHECK_INTERVAL
        
        logger.info("[轮询] 开始轮询循环")
        
        while self.is_polling:
            try:
                # 获取所有活动任务
                active_tasks = await self.tell_active()
                
                # 获取最近停止的任务(可能是快速完成的小文件)
                stopped_tasks = await self.tell_stopped(0, 20)
                
                # 获取等待中的任务
                waiting_tasks = await self.tell_waiting(0, 10)
                
                total_tasks = len(active_tasks) + len(stopped_tasks) + len(waiting_tasks)
                
                if total_tasks > 0:
                    # 遍历活动任务
                    for task in active_tasks:
                        gid = task.get('gid')
                        if not gid:
                            continue
                        await self.sync_download_status(gid, task)
                    
                    # 遍历已停止的任务(可能是complete/error)
                    for task in stopped_tasks:
                        gid = task.get('gid')
                        if not gid:
                            continue
                        # 只处理未记录在completed_gids中的任务
                        if gid not in self.completed_gids:
                            await self.sync_download_status(gid, task)
                    
                    # 遍历等待中的任务
                    for task in waiting_tasks:
                        gid = task.get('gid')
                        if not gid:
                            continue
                        await self.sync_download_status(gid, task)
                    
                    # 有任务时使用正常轮询间隔
                    await asyncio.sleep(POLL_INTERVAL)
                else:
                    # 无任务时使用较长的检查间隔
                    await asyncio.sleep(IDLE_CHECK_INTERVAL)
                    
            except asyncio.CancelledError:
                logger.info("[轮询] 轮询任务被取消")
                break
            except Exception as e:
                logger.exception(f"[轮询] 轮询过程出错: {e}")
                # 出错后等待一段时间再继续
                await asyncio.sleep(POLL_INTERVAL)
        
        logger.info("[轮询] 轮询循环结束")
    
    async def sync_download_status(self, gid: str, aria2_status: dict):
        """
        同步单个下载任务的状态
        
        Args:
            gid: 任务GID
            aria2_status: aria2返回的任务状态信息
        """
        try:
            from db import get_download_by_id, get_download_id_by_gid, mark_download_paused, mark_download_resumed
            
            status = aria2_status.get('status')
            
            # 检查是否已经处理过完成状态
            if gid in self.completed_gids:
                # 已处理过,跳过
                return
            
            logger.info(f"[同步] 任务 {gid[:8]}... 状态: {status}")
            
            # 获取数据库中的当前状态
            download_id = get_download_id_by_gid(gid)
            db_status = None
            if download_id:
                download = get_download_by_id(download_id)
                if download:
                    db_status = download.get('status')
            
            # 根据aria2状态触发相应处理
            if status == 'active':
                # 任务正在下载
                # 如果数据库状态是 paused，说明任务从暂停恢复
                if db_status == 'paused':
                    logger.info(f"[同步] 检测到任务 {gid[:8]}... 从暂停恢复,更新状态")
                    mark_download_resumed(gid)
                
                # 检查是否有对应的消息对象,如果没有说明可能错过了开始事件
                if gid not in self.download_messages:
                    logger.info(f"[同步] 检测到活动任务 {gid[:8]}... 但无消息记录,触发开始事件")
                    # 构造事件结构并触发开始处理
                    event = {
                        'method': 'aria2.onDownloadStart',
                        'params': [{'gid': gid}]
                    }
                    await self.download_handler.on_download_start(event, self.tell_status)
                # 如果有消息对象,进度更新由WebSocket通知处理,轮询不重复更新
                
            elif status == 'waiting':
                # 任务等待中
                # 如果数据库状态是 paused，说明任务从暂停恢复
                if db_status == 'paused':
                    logger.info(f"[同步] 检测到任务 {gid[:8]}... 从暂停恢复(等待中),更新状态")
                    mark_download_resumed(gid)
                
                if gid not in self.download_messages:
                    logger.info(f"[同步] 检测到等待任务 {gid[:8]}...,触发开始事件")
                    event = {
                        'method': 'aria2.onDownloadStart',
                        'params': [{'gid': gid}]
                    }
                    await self.download_handler.on_download_start(event, self.tell_status)
            
            elif status == 'paused':
                # 任务已暂停
                # 如果数据库状态不是 paused，更新数据库状态
                if db_status != 'paused':
                    logger.info(f"[同步] ⏸️ 检测到任务 {gid[:8]}... 已暂停,更新数据库状态")
                    mark_download_paused(gid)
                
            elif status == 'complete':
                # 任务已完成
                logger.info(f"[同步] ✅ 检测到任务 {gid[:8]}... 已完成,触发完成事件")
                event = {
                    'method': 'aria2.onDownloadComplete',
                    'params': [{'gid': gid}]
                }
                await self.download_handler.on_download_complete(event, self.tell_status)
                
            elif status == 'error':
                # 任务出错
                error_msg = aria2_status.get('errorMessage', 'Unknown error')
                logger.error(f"[同步] ❌ 检测到任务 {gid[:8]}... 出错: {error_msg},触发错误事件")
                event = {
                    'method': 'aria2.onDownloadError',
                    'params': [{'gid': gid}]
                }
                await self.download_handler.on_download_error(event, self.tell_status)
                
            elif status == 'removed':
                # 任务被移除
                logger.info(f"[同步] 🗑️ 任务 {gid[:8]}... 已被移除")
                # 不触发事件,只记录
                
        except Exception as e:
            logger.exception(f"[同步] 同步任务 {gid[:8]}... 状态时出错: {e}")
