"""
Author       : Li Qingbing(3263109808@qq.com)
Version      : V0.0
Date         : 2024-11-04 14:10:54
Description  : 
"""

import os
import time
from pathlib import Path


class SyncTimeTable:
    def __init__(self):
        self.csv = None
        self.reset()

    def reset(self):
        """重置所有同步数据记录"""
        self.sync_round = 0
        self.t1 = 0.0
        self.t2 = 0.0
        self.t3 = 0.0
        self.t4 = 0.0
        self.offset = 0.0
        self.rtt = 0.0
        self.diff = 0.0

    def start_timer(self):
        return time.perf_counter()

    def elapsed(self, start_time):
        return time.perf_counter() - start_time

    def csv_open(self, path):
        """关闭已打开的文件（如果有），并以写模式打开新文件"""
        self.csv_close()
        
        # 创建文件路径对象
        file_path = Path(path)
        
        # 如果父目录不存在，则递归创建目录
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建文件（如果文件不存在）
        file_path.touch(exist_ok=True)
        
        # 打开文件并写入文件头
        self.csv = file_path.open("w")

    def csv_close(self):
        """关闭 CSV 文件（如果已打开）"""
        if self.csv is not None:
            self.csv.close()
            self.csv = None

    def csv_write_header(self):
        """写入 CSV 文件头"""
        header = "round,t1,t2,t3,t4,offset,rtt,diff"
        self.csv.write(header + "\n")

    def csv_write_line(self):
        """将一轮同步数据写入 CSV 文件"""
        line = f"{self.sync_round},{self.t1},{self.t2},{self.t3},{self.t4},{self.offset},{self.rtt},{self.diff}"
        self.csv.write(line + "\n")

    def record_sync_data(self, sync_data):
        """记录一轮同步数据"""
        self.sync_round += 1
        self.t1 = sync_data["t1"]
        self.t2 = sync_data["t2"]
        self.t3 = sync_data["t3"]
        self.t4 = sync_data["t4"]
        self.offset = sync_data["offset"]
        self.rtt = sync_data["rtt"]
        self.diff = sync_data["diff"]
        self.csv_write_line()
