"""
缩略图生成器

负责:
1. 生成图片缩略图(使用 Pillow)
2. 生成视频缩略图(使用 ffmpeg)
3. 多级缓存管理(内存LRU + 磁盘持久化)
4. 使用WebP格式(更小体积,更好质量)
"""

import os
import hashlib
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timedelta
from functools import lru_cache
from PIL import Image

logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    """缩略图生成器"""
    
    # 支持的图片格式
    IMAGE_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', 
        '.webp', '.tiff', '.ico', '.svg'
    }
    
    # 支持的视频格式
    VIDEO_EXTENSIONS = {
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', 
        '.flv', '.webm', '.m4v', '.mpg', '.mpeg'
    }
    
    def __init__(
        self, 
        cache_dir: str = "/app/cache/thumbnails",
        thumbnail_size: Tuple[int, int] = (400, 400),
        cache_max_age_days: int = 7,
        memory_cache_size: int = 100
    ):
        """
        初始化缩略图生成器
        
        Args:
            cache_dir: 缓存目录
            thumbnail_size: 缩略图尺寸(宽, 高)
            cache_max_age_days: 缓存有效期(天)
            memory_cache_size: 内存缓存大小(LRU)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存(存储缓存路径)
        from functools import lru_cache
        self._get_cached_path = lru_cache(maxsize=memory_cache_size)(self._get_cached_path_impl)
        self.thumbnail_size = thumbnail_size
        self.cache_max_age_days = cache_max_age_days
        
        logger.info(f"缩略图生成器初始化完成,缓存目录: {self.cache_dir}, 尺寸: {thumbnail_size}")
    
    def _get_cache_key(self, remote_name: str, file_path: str) -> str:
        """生成缓存key"""
        # 使用 remote + 文件路径的 hash 作为缓存key
        content = f"{remote_name}:{file_path}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cache_path(self, remote_name: str, file_path: str) -> Path:
        """获取缓存文件路径"""
        cache_key = self._get_cache_key(remote_name, file_path)
        # 按 remote 分组存储
        remote_cache_dir = self.cache_dir / remote_name
        remote_cache_dir.mkdir(parents=True, exist_ok=True)
        return remote_cache_dir / f"{cache_key}.webp"  # 使用WebP格式
    
    def _get_cached_path_impl(self, remote_name: str, file_path: str) -> Optional[Path]:
        """内存缓存的实际实现(被LRU装饰)"""
        cache_path = self._get_cache_path(remote_name, file_path)
        if cache_path.exists() and self._is_cache_valid(cache_path):
            return cache_path
        return None
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """检查缓存是否有效(未过期)"""
        if not cache_path.exists():
            return False
        
        cache_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expiry_time = datetime.now() - timedelta(days=self.cache_max_age_days)
        
        if cache_time < expiry_time:
            logger.info(f"缓存已过期: {cache_path}")
            cache_path.unlink()  # 删除过期缓存
            return False
        
        return True
    
    def is_cached(self, remote_name: str, file_path: str) -> bool:
        """检查缩略图是否已缓存且有效"""
        cache_path = self._get_cache_path(remote_name, file_path)
        
        if not cache_path.exists():
            return False
        
        # 检查缓存是否过期
        cache_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expiry_time = datetime.now() - timedelta(days=self.cache_max_age_days)
        
        if cache_time < expiry_time:
            logger.info(f"缓存已过期: {cache_path}")
            cache_path.unlink()  # 删除过期缓存
            return False
        
        return True
    
    def get_cached_thumbnail(self, remote_name: str, file_path: str) -> Optional[Path]:
        """获取缓存的缩略图路径"""
        if self.is_cached(remote_name, file_path):
            return self._get_cache_path(remote_name, file_path)
        return None
    
    def _is_image(self, file_path: str) -> bool:
        """判断是否为图片文件"""
        ext = Path(file_path).suffix.lower()
        return ext in self.IMAGE_EXTENSIONS
    
    def _is_video(self, file_path: str) -> bool:
        """判断是否为视频文件"""
        ext = Path(file_path).suffix.lower()
        return ext in self.VIDEO_EXTENSIONS
    
    def generate_image_thumbnail(self, source_path: Path, output_path: Path) -> bool:
        """
        生成图片缩略图
        
        Args:
            source_path: 原始图片路径
            output_path: 输出缩略图路径
            
        Returns:
            是否成功
        """
        try:
            logger.info(f"生成图片缩略图: {source_path.name}")
            
            with Image.open(source_path) as img:
                # 转换为 RGB 模式(处理 PNG 透明度等问题)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # 创建白色背景
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 生成缩略图(保持宽高比)
                img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                
                # 保存为 WebP (更小体积,更好质量)
                img.save(output_path, 'WEBP', quality=85, method=4)
            
            logger.info(f"图片缩略图生成成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"生成图片缩略图失败: {e}", exc_info=True)
            return False
    
    def generate_video_thumbnail(self, source_path: Path, output_path: Path) -> bool:
        """
        生成视频缩略图
        
        Args:
            source_path: 原始视频路径
            output_path: 输出缩略图路径
            
        Returns:
            是否成功
        """
        try:
            logger.info(f"生成视频缩略图: {source_path.name}")
            
            # 使用 ffmpeg 提取第1秒的帧并转换为WebP
            cmd = [
                'ffmpeg',
                '-i', str(source_path),
                '-ss', '00:00:01',  # 跳到第1秒
                '-vframes', '1',    # 只提取1帧
                '-vf', f'scale={self.thumbnail_size[0]}:-1',  # 缩放,保持宽高比
                '-c:v', 'libwebp',  # 使用WebP编码器
                '-quality', '85',    # WebP质量
                '-y',               # 覆盖已存在的文件
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"ffmpeg 执行失败: {result.stderr}")
                return False
            
            if not output_path.exists() or output_path.stat().st_size == 0:
                logger.error(f"视频缩略图生成失败: 输出文件不存在或为空")
                return False
            
            logger.info(f"视频缩略图生成成功: {output_path}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"生成视频缩略图超时: {source_path}")
            return False
        except Exception as e:
            logger.error(f"生成视频缩略图失败: {e}", exc_info=True)
            return False
    
    def generate_thumbnail(
        self, 
        remote_name: str,
        file_path: str,
        source_local_path: Path
    ) -> Optional[Path]:
        """
        生成缩略图(自动判断文件类型)
        
        Args:
            remote_name: remote 名称
            file_path: 云盘文件路径
            source_local_path: 文件在 VFS 挂载点的本地路径
            
        Returns:
            缩略图路径,或 None(失败)
        """
        # 检查内存缓存+磁盘缓存
        cached = self._get_cached_path(remote_name, file_path)
        if cached:
            logger.info(f"缓存命中: {file_path}")
            return cached
        
        # 检查源文件是否存在
        if not source_local_path.exists():
            logger.error(f"源文件不存在: {source_local_path}")
            return None
        
        # 获取输出路径
        output_path = self._get_cache_path(remote_name, file_path)
        
        # 根据文件类型生成缩略图
        success = False
        if self._is_image(file_path):
            success = self.generate_image_thumbnail(source_local_path, output_path)
        elif self._is_video(file_path):
            success = self.generate_video_thumbnail(source_local_path, output_path)
        else:
            logger.warning(f"不支持的文件类型: {file_path}")
            return None
        
        if success and output_path.exists():
            return output_path
        
        return None
    
    def clear_old_cache(self):
        """清理过期缓存"""
        logger.info("开始清理过期缓存...")
        expiry_time = datetime.now() - timedelta(days=self.cache_max_age_days)
        cleared_count = 0
        
        for cache_file in self.cache_dir.rglob("*.webp"):
            cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if cache_time < expiry_time:
                cache_file.unlink()
                cleared_count += 1
        
        logger.info(f"清理完成,删除了 {cleared_count} 个过期缓存")
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        total_files = 0
        total_size = 0
        
        for cache_file in self.cache_dir.rglob("*.webp"):
            total_files += 1
            total_size += cache_file.stat().st_size
        
        return {
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir)
        }


# 全局单例
_thumbnail_generator: Optional[ThumbnailGenerator] = None


def get_thumbnail_generator() -> ThumbnailGenerator:
    """获取全局缩略图生成器实例"""
    global _thumbnail_generator
    if _thumbnail_generator is None:
        _thumbnail_generator = ThumbnailGenerator()
    return _thumbnail_generator
