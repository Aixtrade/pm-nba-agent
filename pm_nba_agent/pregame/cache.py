"""缓存管理器，提供内存和文件双层缓存。"""

import json
import os
import time
from pathlib import Path
from typing import Any, Optional


class CacheManager:
    """双层缓存管理器（内存 + 文件）。

    使用方法:
        cache = CacheManager(ttl=3600)
        cache.set('key', {'data': 'value'})
        data = cache.get('key')
    """

    def __init__(self, cache_dir: str = ".cache", ttl: int = 3600):
        """初始化缓存管理器。

        Args:
            cache_dir: 缓存文件存储目录
            ttl: 缓存有效期（秒），默认3600秒（1小时）
        """
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self._memory_cache: dict[str, tuple[Any, float]] = {}

        # 创建缓存目录
        self.cache_dir.mkdir(exist_ok=True)

    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据。

        先查内存缓存，再查文件缓存。

        Args:
            key: 缓存键

        Returns:
            缓存的数据，如果不存在或已过期则返回 None
        """
        # 1. 检查内存缓存
        if key in self._memory_cache:
            data, timestamp = self._memory_cache[key]
            if time.time() - timestamp < self.ttl:
                return data
            else:
                # 过期，删除
                del self._memory_cache[key]

        # 2. 检查文件缓存
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    timestamp = cache_data.get('timestamp', 0)
                    if time.time() - timestamp < self.ttl:
                        data = cache_data.get('data')
                        # 加载到内存缓存
                        self._memory_cache[key] = (data, timestamp)
                        return data
                    else:
                        # 过期，删除文件
                        cache_file.unlink()
            except Exception:
                # 文件损坏，删除
                cache_file.unlink()

        return None

    def set(self, key: str, data: Any) -> None:
        """设置缓存数据。

        同时写入内存和文件缓存。

        Args:
            key: 缓存键
            data: 要缓存的数据
        """
        timestamp = time.time()

        # 1. 写入内存缓存
        self._memory_cache[key] = (data, timestamp)

        # 2. 写入文件缓存
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': timestamp,
                    'data': data
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # 文件写入失败不影响内存缓存
            pass

    def clear(self) -> None:
        """清空所有缓存（内存和文件）。"""
        # 清空内存缓存
        self._memory_cache.clear()

        # 清空文件缓存
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except Exception:
                pass
