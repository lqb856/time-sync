import ctypes
import socket
import time
import struct

from ..make_env import setns


def run_server():
    host = "10.0.1.1"
    port = 123
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"Binding to {host}:{port}")
        sock.bind((host, port))
        print(f"Server started on {host}:{port}")

        while True:
            data, addr = sock.recvfrom(1024)
            print(f"Received request from {addr}")
            current_time = time.time() + 2208988800  # 转换为 NTP 时间戳
            ntp_time = struct.pack("!I", int(current_time))
            sock.sendto(ntp_time, addr)
    except Exception as e:
        print(f"Failed to start server: {e}")
        exit(-1)


if __name__ == "__main__":
    setns("node1")  # 切换到 node1 命名空间
    run_server()
