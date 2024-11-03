import ctypes
import socket
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