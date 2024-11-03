import argparse
import ctypes
import os
import json
import subprocess
import sys
from pyroute2 import IPRoute, IPDB, NetNS
from pyroute2.netlink.exceptions import NetlinkError

libc = ctypes.CDLL("libc.so.6", use_errno=True)
CLONE_NEWNET = 0x40000000
def setns(ns_name):
    # open namespace file
    ns_fd = open(f"/var/run/netns/{ns_name}", "r")
    # acquire file descriptor
    fd = ns_fd.fileno()
    # use setns to enter namespace
    if libc.setns(fd, CLONE_NEWNET) != 0:
        raise OSError(ctypes.get_errno(), "Failed to enter namespace")
    ns_fd.close()

# load config from file
def load_config(file_path):
    with open(file_path, "r") as f:
        return json.load(f)
      
# save config to file for cleanup next time
def save_config(config, file_path):
    with open(file_path, "w") as f:
        json.dump(config, f, indent=4)
    print(f"Saved current configuration to {file_path}")


# create namespace
def create_namespace(ns_name):
    try:
        with NetNS(ns_name, flags=os.O_CREAT) as ns:
            print(f"Created namespace: {ns_name}")
    except NetlinkError as e:
        print(f"Namespace {ns_name} already exists: {e}")
        
# create bridge
def create_bridge(bridge_name):
    try:
        with IPDB() as ipdb:
            bridge = ipdb.create(ifname=bridge_name, kind='bridge')
            bridge.up().commit()
            print(f"Created bridge: {bridge_name}")
    except Exception as e:
        print(f"Failed to create bridge {bridge_name}: {e}")
        exit(-1)

# create veth pairs and connect to bridge
def create_veth_pairs_and_connect_to_bridge(namespaces, bridge_name):
    with IPDB() as ipdb:
        bridge_index = ipdb.interfaces[bridge_name].index
        print(f"Bridge index: {bridge_index}")
        for i, ns in enumerate(namespaces):
            # generate veth pair names
            veth_host = f"veth-{i+1}-host"
            veth_bridge = f"veth-{i+1}-bridge"

            try:
                # create veth pair
                veth = ipdb.create(ifname=veth_host, kind="veth", peer={"ifname": veth_bridge})
                veth.commit()
                print(f"Created veth pair: {veth_host} <-> {veth_bridge}")
            except Exception as e:
                print(f"Failed to create veth pair {veth_host} <-> {veth_bridge}: {e}")
                exit(-1)

            try:
                # connect left side of veth pair to namespace
                ipdb.interfaces[veth_host].net_ns_fd = ns
                ipdb.interfaces[veth_host].up().commit()
                print(f"Moved {veth_host} to namespace {ns}")
            except Exception as e:
                print(f"Failed to move {veth_host} to namespace {ns}: {e}")
                exit(-1)
            
            try:
                # connect right side of veth pair to bridge
                ipdb.interfaces[veth_bridge].master = bridge_index
                ipdb.interfaces[veth_bridge].up().commit()
                print(f"Connected {veth_bridge} to bridge {bridge_name}")
            except Exception as e:
                print(f"Failed to connect {veth_bridge} to bridge {bridge_name}: {e}")
                exit(-1)


# configure interface IP addresses
def configure_interfaces(nodes, ip_addresses):
    for ns_name, ip_addr in zip(nodes, ip_addresses):
        with NetNS(ns_name) as ipr:
            # aquire all interfaces in the namespace and give them IP addresses
            for link in ipr.get_links():
                veth_name = link.get_attr("IFLA_IFNAME")
                print(f"veth_name: {veth_name}")
                if veth_name.startswith(f"veth-"):
                    idx = link["index"]
                    ipr.addr(
                        "add",
                        index=idx,
                        address=ip_addr.split("/")[0],
                        prefixlen=int(ip_addr.split("/")[1]),
                    )
                    ipr.link("set", index=idx, state="up")
                    print(
                        f"Configured {link.get_attr('IFLA_IFNAME')} in {ns_name} with IP {ip_addr}"
                    )

# list interfaces with IP addresses
def list_interfaces_with_ip(ns_name):
    try:
        with NetNS(ns_name) as ns:
            links = ns.get_links()
            for link in links:
                iface_name = link.get_attr("IFLA_IFNAME")
                addr_info = ns.addr("dump", index=link["index"])
                ip_addresses = [
                    addr.get_attr("IFA_ADDRESS")
                    for addr in addr_info
                    if addr.get_attr("IFA_ADDRESS")
                ]
                print(f"Interface: {iface_name}, IP Addresses: {ip_addresses}")
    except Exception as e:
        print(f"Failed to list interfaces in namespace {ns_name}: {e}")


# set traffic control rules
def set_tc_rules(nodes, tc_config):
    delay_ms = tc_config["delay"]  # latency
    loss_percent = tc_config["loss"]  # drop rate
    print(f"Setting TC rules: {delay_ms}ms delay, {loss_percent}% loss")

    for ns_name in nodes:
        with NetNS(ns_name) as ipr:
            # enumerate all interfaces in the namespace
            for link in ipr.get_links():
                if link.get_attr("IFLA_IFNAME").startswith(f"veth-"):
                    # idx = link['index']
                    # try: # FIXME(lqb): pyroute2 kind parameter conflict, so use subprocess
                    #     # 调用 tc() 设置流量控制规则
                    #     ipr.tc('add', 'root', index=idx, handle='1:', kind='netem', 
                    #            latency=delay_ms, loss=loss_percent)
                    #     print(f"Set TC rules on {link.get_attr('IFLA_IFNAME')} in {ns_name}: {delay_ms} delay, {loss_percent} loss")
                    # except Exception as e:
                    #     print(f"Failed to set TC rules on {link.get_attr('IFLA_IFNAME')} in {ns_name}: {e}")
                    
                    # 因为 pyroute2 不支持设置 netem 规则，所以使用 subprocess 调用 tc 命令
                    interface = link.get_attr("IFLA_IFNAME")
                    try:
                        # 在命名空间中执行 tc 命令
                        subprocess.run(['ip', 'netns', 'exec', ns_name, 'tc', 'qdisc', 'add', 
                                        'dev', interface, 'root', 'netem', 
                                        'delay', delay_ms, 'loss', loss_percent], check=True)
                        print(f"Applied TC rules on {interface}: delay {delay_ms}, loss {loss_percent}")
                    except subprocess.CalledProcessError as e:
                        print(f"Failed to set TC rule on {interface}: {e}")


# cleanup
def cleanup(nodes, bridge_name):
    with IPDB() as ipdb:
        # veth pairs
        for i, node in enumerate(nodes):
            veth1 = f"veth-{i+1}-host"
            if veth1 in ipdb.interfaces:
                ipdb.interfaces[veth1].remove().commit()
                print(f"Deleted interface: {veth1}")
            veth2 = f"veth-{i+1}-bridge"
            if veth2 in ipdb.interfaces:
                ipdb.interfaces[veth2].remove().commit()
                print(f"Deleted interface: {veth2}")

        # bridge
        if bridge_name in ipdb.interfaces:
            ipdb.interfaces[bridge_name].remove().commit()
            print(f"Deleted bridge: {bridge_name}")

    # namespaces
    for ns_name in nodes:
        try:
            os.system(f"ip netns delete {ns_name}")
            print(f"Deleted namespace: {ns_name}")
        except Exception as e:
            print(f"Failed to delete namespace {ns_name}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--clear", type=bool, default=False, help="clear all namespaces and veth pairs")
    args = parser.parse_args()
    print(args)
   
    config = load_config("./conf/cluster_config.json")
    
    # read old config, for cleanup
    old_config = load_config("./conf/cluster_config_old.json")

    # cleanup old configuration
    cleanup(old_config["nodes"], "lqb-bridge")

    if not args.clear:
        # 1. create namespaces
        for ns_name in config["nodes"]:
            create_namespace(ns_name)
            
        # 2. create bridge
        create_bridge("lqb-bridge")

        # 3. create veth pairs and connect to bridge
        create_veth_pairs_and_connect_to_bridge(config["nodes"], "lqb-bridge")

        # 3. assign ip addresses to interfaces
        configure_interfaces(config["nodes"], config["ip_addresses"])

        for ns_name in config["nodes"]:
            print(f"Interfaces in namespace {ns_name}:")
            list_interfaces_with_ip(ns_name)

        # set traffic control rules
        set_tc_rules(config["nodes"], config["tc"])
        
        # save current config to file
        save_config(config, "./conf/cluster_config_old.json")

        print("Cluster setup complete.")
