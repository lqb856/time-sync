'''
Author       : Li Qingbing(3263109808@qq.com)
Version      : V0.0
Date         : 2024-11-03 20:44:23
Description  : 
'''
import socket
import time
import struct
from multiprocessing import Process
from pyroute2 import NetNS

from make_env import load_config, setns

# NTP 服务器
def start_ntp_server(host='10.0.0.1', port=123):
    try:
      sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      print(f"Binding to {host}:{port}")
      sock.bind((host, port))
    except Exception as e:
      print(f"Failed to start NTP server: {e}")
      return
    print(f"NTP server started on {host}:{port}")

    while True:
        data, addr = sock.recvfrom(1024)  # 接收数据
        print(f"Received request from {addr}")

        # NTP 时间戳是从 1900 年 1 月 1 日 00:00:00 UTC 开始的
        current_time = time.time() + 2208988800  # 转换为 NTP 时间戳
        ntp_time = struct.pack('!I', int(current_time))  # 打包成网络字节序

        sock.sendto(ntp_time, addr)  # 发送当前时间

# NTP 客户端
def ntp_client(server_ip, port=123):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)  # 设置超时

    # 构造 NTP 请求报文
    request = b'\x1b' + 47 * b'\0'  # NTP 请求格式
    T1 = time.time()  # 发送请求的时间
    sock.sendto(request, (server_ip, port))  # 发送请求

    try:
        # 接收响应
        data, _ = sock.recvfrom(1024)
        T2 = time.time()  # 服务器接收到请求的时间
        # 解析 NTP 时间戳
        ntp_time = struct.unpack('!I', data[40:44])[0]  # 获取时间戳部分
        ntp_time -= 2208988800  # 转换回 Unix 时间戳
        T3 = ntp_time  # 服务器发送当前时间
        T4 = time.time()  # 客户端接收到响应的时间

        # 计算 RTT 和本地时间偏差
        RTT = (T4 - T1) - (T3 - T2)
        offset = ((T2 - T1) + (T3 - T4)) / 2  # 时间偏差

        return ntp_time, offset, RTT
    except socket.timeout:
        print("Request timed out")
        return None, None, None

# NTP 客户端进程
def run_ntp_client(ns_name, server_ip):
    # 进入命名空间
    setns(ns_name)
    print(f"Starting client on node {ns_name} with server ip {server_ip}")
    ntp_time, offset, RTT = ntp_client(server_ip.split("/")[0])
    if ntp_time is not None:
        local_time = time.time()
        precision = abs(local_time - ntp_time)  # 计算同步精度
        print(f"Node {ns_name} synchronized with NTP server.")
        print(f"  NTP Time: {ntp_time}, Local Time: {local_time}, Offset: {offset:.6f}, RTT: {RTT:.6f}, Precision: {precision:.6f} seconds")
    else:
        print(f"Node {ns_name} failed to synchronize with NTP server.")

# 启动 NTP 服务器进程
def run_ntp_server(ns_name, ip_addr):
    # 进入命名空间
    setns(ns_name)
    print(f"Starting server on node {ns_name} with ip {ip_addr}")
    start_ntp_server(host=ip_addr.split("/")[0])

# 主流程
if __name__ == "__main__":
    config = load_config("./conf/cluster_config.json")
    server_ip = config["ip_addresses"][0]

    # 启动 NTP 服务器在第一个节点
    server_process = Process(target=run_ntp_server, args=(config["nodes"][0], server_ip))
    server_process.start()

    # 等待 NTP 服务器启动
    time.sleep(5)

    # 启动每个节点的 NTP 客户端进程
    client_processes = []
    for ns_name in config["nodes"]:
        if ns_name != config["nodes"][0]:  # 除了第一个节点
            client_process = Process(target=run_ntp_client, args=(ns_name, server_ip))  # 使用 localhost 或者 NTP 服务器 IP
            client_process.start()
            client_processes.append(client_process)

    # 等待所有客户端进程完成
    for client_process in client_processes:
        client_process.join()

    # 等待服务器进程完成
    server_process.join()
