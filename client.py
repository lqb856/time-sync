import ctypes
import socket
import sys
import time
import struct

# 获取 libc 中的 setns 方法
libc = ctypes.CDLL("libc.so.6", use_errno=True)
CLONE_NEWNET = 0x40000000

def setns(ns_name):
    # 打开命名空间文件
    ns_fd = open(f"/var/run/netns/{ns_name}", "r")
    # 获取文件描述符
    fd = ns_fd.fileno()
    # 使用 setns 进入命名空间
    if libc.setns(fd, CLONE_NEWNET) != 0:
        raise OSError(ctypes.get_errno(), "Failed to enter namespace")
    ns_fd.close()

def run_client(server = "10.0.1.1"):
    port = 123
    print(f"Connecting to {server}:{port}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        request = b'hello'
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
