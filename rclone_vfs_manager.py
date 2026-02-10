"""
Rclone VFS 挂载管理器

负责:
1. 自动挂载/卸载 rclone remote
2. 挂载状态检查
3. 挂载点管理
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional, List
import threading
import time

logger = logging.getLogger(__name__)


class RcloneVFSManager:
    """Rclone VFS 挂载管理器"""
    
    def __init__(self, mount_base: str = "/mnt/rclone"):
        """
        初始化 VFS 管理器
        
        Args:
            mount_base: 挂载点基础目录
        """
        self.mount_base = Path(mount_base)
        self.mount_base.mkdir(parents=True, exist_ok=True)
        
        # 存储挂载进程
        self._mount_processes: Dict[str, subprocess.Popen] = {}
        # 挂载点路径缓存
        self._mount_points: Dict[str, Path] = {}
        # 挂载锁
        self._mount_lock = threading.Lock()
        
        logger.info(f"VFS Manager 初始化完成,挂载基础目录: {self.mount_base}")
    
    def get_mount_point(self, remote_name: str) -> Path:
        """获取 remote 的挂载点路径"""
        return self.mount_base / remote_name
    
    def is_mounted(self, remote_name: str) -> bool:
        """检查 remote 是否已挂载"""
        mount_point = self.get_mount_point(remote_name)
        
        # 检查挂载点是否存在
        if not mount_point.exists():
            return False
        
        # 检查是否为挂载点
        try:
            result = subprocess.run(
                ["mountpoint", "-q", str(mount_point)],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"检查挂载状态失败: {e}")
            return False
    
    def mount(self, remote_name: str, force: bool = False) -> bool:
        """
        挂载 remote
        
        Args:
            remote_name: remote 名称
            force: 强制重新挂载
            
        Returns:
            是否挂载成功
        """
        with self._mount_lock:
            # 如果已经挂载且不强制重新挂载,直接返回
            if self.is_mounted(remote_name) and not force:
                logger.info(f"Remote {remote_name} 已挂载")
                return True
            
            # 如果强制重新挂载,先卸载
            if force and self.is_mounted(remote_name):
                self.unmount(remote_name)
            
            mount_point = self.get_mount_point(remote_name)
            mount_point.mkdir(parents=True, exist_ok=True)
            
            # 构建 rclone mount 命令
            cmd = [
                "rclone", "mount",
                f"{remote_name}:",
                str(mount_point),
                "--vfs-cache-mode", "full",
                "--vfs-cache-max-age", "24h",
                "--vfs-cache-max-size", "10G",
                "--dir-cache-time", "5m",
                "--allow-other",  # 允许其他用户访问
                "--daemon",  # 后台运行
            ]
            
            try:
                logger.info(f"挂载 {remote_name} 到 {mount_point}")
                logger.debug(f"执行命令: {' '.join(cmd)}")
                
                # 执行挂载命令
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    logger.error(f"挂载失败: {result.stderr}")
                    return False
                
                # 等待挂载完成
                time.sleep(2)
                
                # 验证挂载是否成功
                if self.is_mounted(remote_name):
                    logger.info(f"Remote {remote_name} 挂载成功")
                    self._mount_points[remote_name] = mount_point
                    return True
                else:
                    logger.error(f"挂载验证失败: {remote_name}")
                    return False
                    
            except subprocess.TimeoutExpired:
                logger.error(f"挂载超时: {remote_name}")
                return False
            except Exception as e:
                logger.error(f"挂载异常: {e}", exc_info=True)
                return False
    
    def unmount(self, remote_name: str) -> bool:
        """
        卸载 remote
        
        Args:
            remote_name: remote 名称
            
        Returns:
            是否卸载成功
        """
        with self._mount_lock:
            if not self.is_mounted(remote_name):
                logger.info(f"Remote {remote_name} 未挂载,无需卸载")
                return True
            
            mount_point = self.get_mount_point(remote_name)
            
            try:
                logger.info(f"卸载 {remote_name} (挂载点: {mount_point})")
                
                # 使用 fusermount 卸载
                result = subprocess.run(
                    ["fusermount", "-u", str(mount_point)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    logger.warning(f"fusermount 卸载失败,尝试 umount: {result.stderr}")
                    # 尝试使用 umount
                    result = subprocess.run(
                        ["umount", str(mount_point)],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                
                # 等待卸载完成
                time.sleep(1)
                
                # 验证卸载
                if not self.is_mounted(remote_name):
                    logger.info(f"Remote {remote_name} 卸载成功")
                    if remote_name in self._mount_points:
                        del self._mount_points[remote_name]
                    return True
                else:
                    logger.error(f"卸载验证失败: {remote_name}")
                    return False
                    
            except Exception as e:
                logger.error(f"卸载异常: {e}", exc_info=True)
                return False
    
    def get_file_path(self, remote_name: str, file_path: str) -> Optional[Path]:
        """
        获取文件在挂载点的完整路径
        
        Args:
            remote_name: remote 名称
            file_path: 云盘文件路径(相对路径)
            
        Returns:
            本地文件路径,或 None(如果未挂载)
        """
        if not self.is_mounted(remote_name):
            logger.warning(f"Remote {remote_name} 未挂载")
            return None
        
        mount_point = self.get_mount_point(remote_name)
        # 去掉路径开头的 /
        clean_path = file_path.lstrip('/')
        return mount_point / clean_path
    
    def ensure_mounted(self, remote_name: str) -> bool:
        """
        确保 remote 已挂载,如果未挂载则自动挂载
        
        Args:
            remote_name: remote 名称
            
        Returns:
            是否挂载成功
        """
        if self.is_mounted(remote_name):
            return True
        
        return self.mount(remote_name)
    
    def list_mounted_remotes(self) -> List[str]:
        """列出所有已挂载的 remote"""
        mounted = []
        for remote_name in os.listdir(self.mount_base):
            if self.is_mounted(remote_name):
                mounted.append(remote_name)
        return mounted
    
    def cleanup(self):
        """清理所有挂载"""
        logger.info("清理所有 VFS 挂载...")
        mounted = self.list_mounted_remotes()
        for remote_name in mounted:
            self.unmount(remote_name)


# 全局单例
_vfs_manager: Optional[RcloneVFSManager] = None


def get_vfs_manager() -> RcloneVFSManager:
    """获取全局 VFS 管理器实例"""
    global _vfs_manager
    if _vfs_manager is None:
        _vfs_manager = RcloneVFSManager()
    return _vfs_manager
