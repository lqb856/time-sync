import ctypes
import socket
import sys
import time
import struct

from ..make_env import setns


def run_client(server="10.0.1.1"):
    port = 123
    print(f"Connecting to {server}:{port}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        request = b"hello"
        sock.sendto(request, (server, port))
        data, _ = sock.recvfrom(1024)
        print(f"Received response: {data}")
    except Exception as e:
        print(f"Failed to start server: {e}")
        exit(-1)


if __name__ == "__main__":
    args = sys.argv
    setns(args[1])  # 切换到 node1 命名空间
    run_client(args[2])
