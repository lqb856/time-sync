"""
Author       : Li Qingbing(3263109808@qq.com)
Version      : V0.0
Date         : 2024-11-03 20:44:23
Description  : 
"""

import argparse
import random
import socket
import time
import struct
from multiprocessing import Process

from make_env import load_config, setns
from algorithms import *
from status import SyncTimeTable


# server
def start_server(name, host="10.0.0.1", port=123, algorithm=NTPAlgorithm()):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((host, port))
    except Exception as e:
        print(f"Failed to start server: {e}")
        exit(-1)
    print(f"server started on {host}:{port}")

    sock.settimeout(5)  # timeout 5s
    while True:
        try:
            """
            server code here.
            """
            algorithm.server_process(name, sock)
        except Exception as e:
            print(f"Failed in server: {e}")


# client
def start_client(name, server_ip, port=123, latency: int = 50, algorithm=NTPAlgorithm()):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)  # timeout 5s
    # randomize the offset
    random.seed(time.time())
    algorithm.cumulative_offset = random.uniform(-0.5, 0.5)
    st = SyncTimeTable()
    st.csv_open("./data/" + algorithm.get_name() + "-" + str(latency) + "ms" + "/" + name + ".csv")
    st.csv_write_header()
    while True:
        try:
            """
            client code here.
            """
            sync_data = algorithm.client_process(name, sock, server_ip, port)
            st.record_sync_data(sync_data)
            if algorithm.get_name() != "Berkeley":
                time.sleep(random.uniform(0.5, 1.5))
            else:
                time.sleep(1)
        except socket.timeout:
            continue
        except Exception as e:
            st.csv_close()
            print(f"Failed in client: {e}")
            exit(-1)


# run client process
def run_client(ns_name, server_ip, latency: int = 50, algorithm=NTPAlgorithm()):
    # 进入命名空间
    setns(ns_name)
    print(f"Starting client on node {ns_name} with server ip {server_ip}")
    start_client(ns_name, server_ip.split("/")[0], latency=latency, algorithm=algorithm)


# run server process
def run_server(ns_name, ip_addr, algorithm=NTPAlgorithm()):
    # 进入命名空间
    setns(ns_name)
    print(f"Starting server on node {ns_name} with ip {ip_addr}")
    start_server(ns_name, host=ip_addr.split("/")[0], algorithm=algorithm)

def get_algorithm_instance(algorithm_name):
    if algorithm_name == "ntp":
        return NTPAlgorithm()
    elif algorithm_name == "cristian":
        return CristianAlgorithm()
    elif algorithm_name == "berkeley":
        return BerkeleyAlgorithm()
    else:
        print(f"Unsupportted algorithm: {algorithm_name}")
        exit(-1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a", "--algorithm", default="ntp", help="Clock synchronization algorithm (ntp, cristian, berkeley)"
    )
    parser.add_argument(
        "-l", "--latency", type=int, default=50, help="Latency in ms for network delay simulation"
    )
    args = parser.parse_args()
    print(args)
    
    config = load_config("./conf/cluster_config.json")
    server_ip = config["ip_addresses"][0]

    # 启动 NTP 服务器在第一个节点
    server_process = Process(target=run_server, args=(config["nodes"][0], server_ip, get_algorithm_instance(args.algorithm)))
    server_process.start()

    # 等待 NTP 服务器启动
    time.sleep(3)

    # 启动每个节点的 NTP 客户端进程
    client_processes = []
    for ns_name in config["nodes"]:
        if ns_name != config["nodes"][0]:  # 除了第一个节点
            client_process = Process(
                target=run_client, args=(ns_name, server_ip, args.latency, get_algorithm_instance(args.algorithm))
            )  # 使用 localhost 或者 NTP 服务器 IP
            client_process.start()
            client_processes.append(client_process)

    # 等待所有客户端进程完成
    for client_process in client_processes:
        client_process.join()

    # 等待服务器进程完成
    server_process.join()
