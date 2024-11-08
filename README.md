# 1. **make_env.py 工作原理**

> 作者: 黎清兵
>
> 邮箱: <3263109808@qq.com>

make_env.py 脚本旨在创建和配置一个虚拟网络环境，模拟多个计算节点之间的通信。

该虚拟环境由一系列的 Namespace（虚拟节点）、 Veth（虚拟以太网）以及虚拟的网桥构成。

各个虚拟节点通过虚拟的网桥和交换机连接，构成了一个星型的拓扑结构（中间时网桥，四周是节点，节点和网桥虚拟以太网连接）。

该脚本的主要功能包括：

## 1. **命名空间管理：**

它创建多个 Linux 命名空间，每个命名空间代表一个独立的网络环境，模拟不同的计算节点。

为每个命名空间分配虚拟以太网接口，以便于它们之间的通信。

## 2. **虚拟以太网对 (veth pairs)：**

为每对命名空间创建一对虚拟以太网接口（veth pairs），一端连接到一个命名空间，另一端连接到一个公共网桥。

这种设置允许命名空间之间进行网络连接。

## 3. **桥接配置：**

创建一个虚拟桥接，将来自不同命名空间的所有 veth 接口连接到一起，从而实现网络流量的转发。

桥接促进了不同命名空间之间的高效点对点通信。

## 4. **网络接口设置：**

为每个 veth 接口配置网络参数，如 IP 地址和子网掩码，确保所有节点可以在同一网络上识别和相互通信。

通过这些步骤，make_env.py 脚本提供了模拟集群环境的基础设施，允许不同命名空间中的进程进行交互和数据传输，就像它们处于同一物理网络上一样。

# 2. 如何使用 make_env.py

脚本使用了 `pyroute2`、`json` 等包，请确保你的 python 环境中安装了它们。

## 1. 编辑 cluster_config.json

- 添加你的节点
- 为每个节点声明 IP
- 设置延迟和丢包率

> 注意：请勿修改 **cluster_config_old.json**，该文件用于清理环境。

## 2. 运行 make-env.py

```shell
sudo [你的_python_解释器] make-env.py
```

例如：`sudo ~/anaconda3/envs/py39/bin/python3.9 make_env.py`

## 3. 检查节点和链接是否成功构建

1. **查询节点**

```shell
ip netns list
```

1. **查询每个节点的链接**

```shell
sudo ip netns exec [节点名称] ip -d link show
```

1. **查询每个节点的 tc**

```shell
sudo ip netns exec [节点名称] tc -s qdisc show
```

1. **查询桥接及其连接的 veth**

```shell
bridge fdb show br [桥接名称]
```

## 4. 使用创建的节点运行你的程序

1. 通过命令行运行

```shell
ip netns exec <命名空间> ./your_program
```

2. 通过 Python 代码运行

```python
from make_env import *

setns("node1")  # 切换到 node1 命名空间
'''
  your code
  使用普通套接字编程即可
'''
```

# 3. More debugging techniques

## 1. 检查网络连接和路由

确保客户端和服务器所在的命名空间之间的路由正确。例如，如果服务器在 `node1` 命名空间中，客户端在 `node2` 中，确保两者之间可以互相通信。可以通过 `ping` 命令验证：

```bash
sudo ip netns exec node1 ping 10.0.1.2  # 假设客户端的 IP 是 10.0.1.2
```

如果 `ping` 不通，则需要检查是否正确配置了网桥、子网和接口。

## 2. 确认防火墙配置

确保防火墙规则没有阻止 UDP 流量。可以临时关闭防火墙来排除这个因素：

```bash
sudo ip netns exec node1 ufw disable  # 或者使用 iptables 检查并清除相关规则
```

## 3. 确保接口都处于 `UP` 状态

在服务器和客户端命名空间中，确保 `veth` 接口和网桥都处于 `UP` 状态：

```bash
sudo ip netns exec node1 ip link set dev veth-1-host up
sudo ip netns exec node2 ip link set dev veth-2-host up
sudo ip link set dev lqb-bridge up
```

## 4. 检查网桥和命名空间配置

确认网桥是否成功将所有虚拟接口连接到一起，并且接口没有错配。可以通过以下命令检查网桥配置：

```shell
brctl show lqb-bridge  # 列出所有连接到网桥的端口
```

## 5. 使用 `tcpdump` 检查流量

在发送和接收节点上使用 `tcpdump` 检查流量是否正常到达，帮助定位阻塞点。可以在 `node1` 中监听端口 123：

```shell
sudo ip netns exec node1 tcpdump -i veth-1-host port 123
```
