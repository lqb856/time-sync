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


class CristianAlgorithm(ClockSyncAlgorithm):
    def __init__(self):
        super().__init__()
        
    def get_name(self):
        return "Cristian"

    def server_process(self, name, sock: socket.socket, num_client: int = 3) -> None:
        """
        服务器端的 Cristian 处理逻辑
        """
        # 接收客户端请求数据
        data, addr = sock.recvfrom(1024)
        t2 = time.time()  # 服务器接收到请求的时间戳
        print(f"{name} received request from {addr}")

        # 构建 Cristian 响应，发送当前时间 t2
        response = struct.pack("!d", t2)

        # 发送响应
        sock.sendto(response, addr)
        print(f"{name} sent time to {addr}")

    def client_process(
        self, name, sock: socket.socket, server_ip: str, server_port: int
    ) -> dict:
        """
        客户端的 Cristian 处理逻辑
        """
        t1 = self.get_simulated_time()  # 客户端发送请求的时间戳
        sock.sendto(b"", (server_ip, server_port))

        # 接收服务器响应并提取 t2 时间戳
        data, _ = sock.recvfrom(1024)
        t4 = self.get_simulated_time()  # 客户端接收响应的时间戳
        t2 = struct.unpack("!d", data)[0]

        # 计算往返时间 RTT
        rtt = t4 - t1

        # 估算的偏移量和更新时间
        offset = (t2 - t1) + (rtt / 2)
        # 累计时间偏移
        self.accumulate_offset(offset)
        updated_time = t4 + offset
        current_system_time = time.time()
        diff = abs(updated_time - current_system_time)

        print(
            f"{name} Cristian sync results: t1={t1}, t2={t2}, t4={t4}, offset={offset}, rtt={rtt}, diff={diff}"
        )

        # 返回结果用于记录到 CSV
        return {
            "t1": t1,
            "t2": t2,
            "t3": None,
            "t4": t4,
            "offset": offset,
            "rtt": rtt,
            "diff": diff,
        }
