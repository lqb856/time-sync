"""
Author       : Li Qingbing(3263109808@qq.com)
Version      : V0.0
Date         : 2024-11-04 13:52:23
Description  : 
"""

import struct
import time
import socket
from clock_sync_algorithm import ClockSyncAlgorithm


class NTPAlgorithm(ClockSyncAlgorithm):
    def __init__(self):
        super().__init__()
        
    def get_name(self):
        return "NTP"

    def server_process(self, name, sock: socket.socket, num_client: int = 3) -> None:
        """
        服务器端的 NTP 处理逻辑
        """
        # 接收客户端请求数据
        data, addr = sock.recvfrom(1024)
        t2 = time.time()  # 服务器接收到请求的时间戳
        # print(f"{name} received request from {addr}")

        # 构建 NTP 响应，包含 t2 和 t3（发送时间）
        t3 = time.time()  # 服务器发送响应的时间戳
        response = struct.pack("!d", t2) + struct.pack("!d", t3)

        # 发送响应
        sock.sendto(response, addr)
        # print(f"{name} sent response to {addr}")

    def client_process(
        self, name, sock: socket.socket, server_ip: str, server_port: int
    ) -> dict:
        """
        客户端的 NTP 处理逻辑
        """
        t1 = self.get_simulated_time()  # 客户端发送请求的时间戳
        sock.sendto(b"", (server_ip, server_port))

        # 接收服务器响应并提取 t2 和 t3 时间戳
        data, _ = sock.recvfrom(1024)
        t4 = self.get_simulated_time()  # 客户端接收响应的时间戳
        t2, t3 = struct.unpack("!d d", data)

        # 计算时间偏移量和往返时间
        offset = ((t2 - t1) + (t3 - t4)) / 2
        # 累计时间偏移
        self.accumulate_offset(offset)
        rtt = (t4 - t1)

        # 更新后的系统时间
        updated_time = t4 + offset
        current_system_time = time.time()
        diff = abs(updated_time - current_system_time)

        print(
            f"{name} NTP sync results: t1={t1}, t2={t2}, t3={t3}, t4={t4}, offset={offset}, rtt={rtt}, diff={diff}"
        )

        # 返回结果用于记录到 CSV
        return {
            "t1": t1,
            "t2": t2,
            "t3": t3,
            "t4": t4,
            "offset": offset,
            "rtt": rtt,
            "diff": diff,
        }
