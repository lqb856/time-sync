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


class BerkeleyAlgorithm(ClockSyncAlgorithm):
    def __init__(self):
        super().__init__()
        
    def get_name(self):
        return "Berkeley"

    def server_process(self, name, sock: socket.socket, num_client: int = 3) -> None:
        """
        协调者处理逻辑
        """
        clients_times = []

        # 1. 向所有客户端请求当前时间
        for _ in range(num_client):
            try:
                # 接收客户端时间请求
                data, addr = sock.recvfrom(1024)
                client_time = struct.unpack("!d", data)[0]
                clients_times.append((addr, client_time))
                # print(f"{name} received time from {addr}: {client_time}")
            except socket.timeout:
                print(f"{name} timeout waiting for client response")

        if not clients_times:
            print(f"{name} did not receive any client times")
            return

        # 2. 计算时间偏移
        # 获取协调者的时间
        coordinator_time = self.get_simulated_time_server()
        all_times = [time for _, time in clients_times] + [coordinator_time]

        # 计算平均时间
        avg_time = sum(all_times) / len(all_times)

        # 计算偏移量并过滤掉偏差过大的客户端
        time_offsets = {}
        for addr, client_time in clients_times:
            offset = avg_time - client_time
            time_offsets[addr] = offset

        coordinator_offset = avg_time - coordinator_time
        self.accumulate_offset_server(coordinator_offset)  # 更新协调者的时间偏移量
        # print(
        #     f"{name} calculated offsets for clients and self. Coordinator offset: {coordinator_offset}"
        # )

        # 3. 向客户端发送调整值
        for addr, offset in time_offsets.items():
            adjustment = struct.pack("!d", offset)
            sock.sendto(adjustment, addr)
            # print(f"{name} sent offset {offset} to {addr}")

    def client_process(
        self, name, sock: socket.socket, server_ip: str, server_port: int
    ) -> dict:
        """
        客户端处理逻辑
        """
        t1 = self.get_simulated_time()  # 模拟时间
        sock.sendto(struct.pack("!d", t1), (server_ip, server_port))

        # 接收协调者的调整量
        adjustment = -1 # 没有收到调整量
        try:
            data, _ = sock.recvfrom(1024)
            adjustment = struct.unpack("!d", data)[0]
            self.accumulate_offset(adjustment)  # 更新客户端的时间偏移量
            # print(
            #     f"{name} received adjustment {adjustment}. Updated cumulative offset: {self.cumulative_offset}"
            # )
        except socket.timeout:
            print(f"{name} did not receive adjustment from coordinator")

        # 返回同步后的模拟时间与系统时间的差异
        current_system_time = time.time()
        simulated_time = self.get_simulated_time()
        diff = abs(simulated_time - current_system_time)

        print(
            f"{name} Berkeley sync results: t1={t1}, adjustment={adjustment}, cumulative_offset={self.cumulative_offset}, diff={diff}"
        )

        return {
            "t1": t1,
            "t2": None,
            "t3": None,
            "t4": None,
            "offset": adjustment,
            "rtt": None,
            "diff": diff,
        }
