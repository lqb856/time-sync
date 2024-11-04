"""
Author       : Li Qingbing(3263109808@qq.com)
Version      : V0.0
Date         : 2024-11-03 20:44:23
Description  : 
"""

import argparse
import socket
import time
import struct
from multiprocessing import Process

from make_env import load_config, setns
from .algorithms import *
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

    while True:
        try:
            """
            server code here.
            """
            algorithm.server_process(name, sock)
        except Exception as e:
            print(f"Failed in server: {e}")


# client
def start_client(name, server_ip, port=123, algorithm=NTPAlgorithm()):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)  # timeout 2s
    st = SyncTimeTable()
    st.csv_open("./data/" + name + ".csv")
    st.csv_write_header()
    while True:
        try:
            """
            client code here.
            """
            sync_data = algorithm.client_process(name, sock, server_ip, port, algorithm)
            st.record_sync_data(sync_data)
        except socket.timeout:
            print("Request timed out")
            st.csv_close()
            exit(-1)
        except Exception as e:
            st.csv_close()
            print(f"Failed in server: {e}")
            exit(-1)


# run client process
def run_client(ns_name, server_ip, algorithm=NTPAlgorithm()):
    # 进入命名空间
    setns(ns_name)
    print(f"Starting client on node {ns_name} with server ip {server_ip}")
    start_client(ns_name, server_ip.split("/")[0], algorithm=algorithm)


# run server process
def run_server(ns_name, ip_addr, algorithm=NTPAlgorithm()):
    # 进入命名空间
    setns(ns_name)
    print(f"Starting server on node {ns_name} with ip {ip_addr}")
    start_server(ns_name, host=ip_addr.split("/")[0], algorithm=algorithm)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a", "--algorithm", default="ntp", help="clear all namespaces and veth pairs"
    )
    args = parser.parse_args()
    print(args)

    # TODO(lqb): a algorithm instance for each client
    # if args['a'] == "ntp":
    #     algorithm = NTPAlgorithm()
    # elif args["a"] == "cristian":
    #     algorithm = CristianAlgorithm()
    # elif args["a"] == "berkeley":
    #     algorithm = BerkeleyAlgorithm()
    # else:
    #     print(f"Unsupportted algorithm: {args['a']}")
    #     exit(-1)
    
    config = load_config("./conf/cluster_config.json")
    server_ip = config["ip_addresses"][0]

    # 启动 NTP 服务器在第一个节点
    server_process = Process(target=run_server, args=(config["nodes"][0], server_ip))
    server_process.start()

    # 等待 NTP 服务器启动
    time.sleep(3)

    # 启动每个节点的 NTP 客户端进程
    client_processes = []
    for ns_name in config["nodes"]:
        if ns_name != config["nodes"][0]:  # 除了第一个节点
            client_process = Process(
                target=run_client, args=(ns_name, server_ip)
            )  # 使用 localhost 或者 NTP 服务器 IP
            client_process.start()
            client_processes.append(client_process)

    # 等待所有客户端进程完成
    for client_process in client_processes:
        client_process.join()

    # 等待服务器进程完成
    server_process.join()
