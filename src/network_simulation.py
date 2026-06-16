import glob
import ipaddress
import json
import os
import random
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
from time import sleep
from typing import Optional, Union

import docker
import networkx as nx
import matplotlib.pyplot as plt
from docker.models.networks import Network

from .ip_tools import IPAddressAllocator
from .nodes import RouterNode, LISPNode, ClientNode, FrrOSPFRouterNode, Node


class NetworkSimulation:
    def __init__(self):
        self.nodes = []  # 所有节点
        self.router_nodes = []  # 路由节点
        self.xtr_nodes = []  # xtr节点
        self.msmr_nodes = []  # ms节点
        self.client_nodes = []  # 客户端节点

        self.base_network = ipaddress.ip_network("10.10.0.0/16")  # 可用的网络范围
        self.subnet_prefixlen = 24  # 子网前缀
        self.graph = nx.Graph()  # networkx图
        self.client = docker.from_env()  # docker客户端
        self.net_docker_obj = {}  # 所有docker网络对象
        self.networks = {}  # 所有网络
        self.ip_allocator = IPAddressAllocator()  # ip分配工具
        self.is_running = False
        self.group_label = "network_simulation_group"  # docker标签
        self.next_subnet = iter(self.base_network.subnets(new_prefix=self.subnet_prefixlen))  # 子网迭代器

    def cleanup(self):
        print('开始清理容器和网络……')
        # 清理容器
        containers = self.client.containers.list(all=True, filters={"label": f"group={self.group_label}"})
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self._stop_and_remove_container, container) for container in containers]
            for future in futures:
                future.result()

        # 清理网络
        networks = self.client.networks.list(filters={"label": f"group={self.group_label}"})
        for network in networks:
            try:
                network.remove()
                print(f'-> 网络{network.name}已停止并删除')
            except Exception as e:
                print(f"Failed to remove network {network.name}: {str(e)}")

        self.reset_all()
        self.cleanup_config_files()
        print('全部清理完毕')

    @staticmethod
    def _stop_and_remove_container(container):
        """停止并删除单个容器"""
        try:
            container.stop()
            container.remove()
            print(f'-> 容器{container.name}已停止并删除')
        except docker.errors.APIError as e:
            print(f"Failed to stop or remove container {container.name}: {str(e)}")

    def create_network(self):
        subnet = next(self.next_subnet)
        net_name = f'bjtu_{subnet}'
        network = self.client.networks.create(
            net_name,
            driver="bridge",
            labels={"group": self.group_label},  # 添加唯一标签
            # options={"com.docker.network.bridge.name": f"br-{subnet.network_address}"},  # 主机中网桥名称
            # options={"com.docker.network.container_iface_prefix": f"RLOC"},  # 容器中网卡名称前缀
            ipam=docker.types.IPAMConfig(
                pool_configs=[
                    docker.types.IPAMPool(
                        subnet=str(subnet)
                    )
                ]
            )
        )
        self.net_docker_obj[net_name] = network
        self.networks[net_name] = subnet
        self.ip_allocator.add_network(subnet)
        print(f"-> 网络{subnet}创建成功")
        return net_name

    def create_manual_network(self, network_cidr):
        subnet = ipaddress.ip_network(network_cidr)
        net_name = f'bjtu_{subnet}'
        network = self.client.networks.create(
            net_name,
            driver="bridge",
            labels={"group": self.group_label},  # 添加唯一标签
            ipam=docker.types.IPAMConfig(
                pool_configs=[
                    docker.types.IPAMPool(
                        subnet=str(subnet)
                    )
                ]
            )
        )
        self.net_docker_obj[net_name] = network
        self.networks[net_name] = subnet
        print(f"-> 网络{subnet}创建成功")
        return net_name

    def create_macvlan_network(self, net_name, parent, subnet, gateway):
        network = self.client.networks.create(
            net_name,
            driver="macvlan",
            options={"parent": str(parent)},
            labels={"group": self.group_label},  # 添加唯一标签
            ipam=docker.types.IPAMConfig(
                driver="default",
                pool_configs=[docker.types.IPAMPool(
                    subnet=str(subnet),
                    gateway=str(gateway)
                )]
            )
        )
        self.net_docker_obj[net_name] = network
        self.networks[net_name] = subnet
        return net_name

    def create_random_nodes(self, count):
        print(f'开始创建{count}个节点的随机拓扑……')
        nodes = [f"node_{i + 1}" for i in range(count)]
        edges = set()
        node_connections = {node: 0 for node in nodes}  # 记录每个节点的连接数

        if count == 1:
            # 对于单个节点的情况，不生成边，直接返回单节点拓扑
            self.create_custom_topology(nodes, list(edges))
            return

        # 生成随机边
        max_conn = 2 if count >= 3 else count
        for node in nodes:
            possible_connections = random.sample(nodes, k=random.randint(1, max_conn))
            for target_node in possible_connections:
                if node != target_node:
                    # 使用排序的元组表示无向边，避免重复
                    edge = tuple(sorted((node, target_node)))
                    if edge not in edges:
                        edges.add(edge)
                        # 增加每个节点的连接计数
                        node_connections[node] += 1
                        node_connections[target_node] += 1

        # 确保每个节点至少有一个连接
        for node in nodes:
            if node_connections[node] == 0:
                # 随机选择一个不同的节点来连接
                while True:
                    target_node = random.choice(nodes)
                    if node != target_node:
                        edge = tuple(sorted((node, target_node)))
                        if edge not in edges:
                            edges.add(edge)
                            # 更新连接计数
                            node_connections[node] += 1
                            node_connections[target_node] += 1
                            break

        self.create_custom_topology(self.get_nodes_js(nodes), list(edges))

    def create_circle_nodes(self, count):
        print(f'开始创建{count}个节点的环形拓扑……')
        nodes = [f"node_{i + 1}" for i in range(count)]
        edges = []
        # 生成环形边
        for i in range(count):
            edges.append([nodes[i], nodes[(i + 1) % count]])
        self.create_custom_topology(self.get_nodes_js(nodes), list(edges))

    def create_grid_nodes(self, rows, cols):
        print(f'开始创建{rows}行{cols}列的网格拓扑……')
        nodes = [f"node_{i * cols + j + 1}" for i in range(rows) for j in range(cols)]
        edges = []
        # 生成网格边
        for i in range(rows):
            for j in range(cols):
                node_index = i * cols + j
                if j < cols - 1:  # 水平边（右）
                    edges.append([nodes[node_index], nodes[node_index + 1]])
                if i < rows - 1:  # 垂直边（下）
                    edges.append([nodes[node_index], nodes[node_index + cols]])
        self.create_custom_topology(self.get_nodes_js(nodes), list(edges))

    @staticmethod
    def get_nodes_js(nodes):
        nodes_js = []
        for node in nodes:
            nodes_js.append({"name": node, "type": "Router", "coordinates": {"latitude": 0.0, "longitude": 0.0}})
        return nodes_js


    def create_custom_topology(self, nodes: list, edges: list):
        """
        通过提供的节点和边创建自定义拓扑。
        :param nodes: 节点名称的列表，例如 [{"name":"node_1","type":"router","coordinates":{"latitude":39.906217,"longitude":116.3912757}}]
        :param edges: 边的列表，每个边表示为 (节点1, 节点2)，例如 [('node1', 'node2'), ('node2', 'node3')]
        """
        print('开始创建拓扑……')
        # 创建节点
        for node_js in nodes:
            node_name = node_js['name']
            # node = FrrOSPFRouterNode(node_name, self.ip_allocator, self.group_label, self.networks)
            node = RouterNode(node_name, self.ip_allocator, self.group_label, self.networks)
            node.coordinates = node_js['coordinates']
            self.router_nodes.append(node)
            self.graph.add_node(node_name)

        # 添加边并为每条边创建网络
        for edge in edges:
            network_name = self.create_network()
            self.graph.add_edge(edge[0], edge[1], network=network_name)

            # 为每个节点分配 IP 地址
            for node_name in edge:
                node = next(node for node in self.router_nodes if node.name == node_name)
                node.assign_ip(network_name)
        self.nodes.extend(self.router_nodes)
        print('创建完毕')

    def start_simulation(self):
        print('正在启动仿真……')
        nodes_chunk = list(self._chunk_list(self.nodes, 10))
        for chunk in nodes_chunk:
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(node.start) for node in chunk]
                for future in futures:
                    future.result()
        # for node in self.nodes:
        #     node.start()

        self.is_running = True
        print('仿真启动完毕')

    @staticmethod
    def _chunk_list(lst, chunk_size):
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]

    def stop_simulation(self):
        print('正在停止仿真……')
        # if not self.is_running:
        #     raise RuntimeError("Simulation is not running")

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(node.stop) for node in self.nodes]
            for future in futures:
                future.result()

        # 删除Docker网络
        for network in self.net_docker_obj.values():
            network.remove()

        self.reset_all()
        self.is_running = False
        print('仿真已停止')

    def reset_all(self):
        # 清理网络
        self.net_docker_obj.clear()
        self.networks.clear()
        # 清空现有节点和图结构
        self.nodes.clear()
        self.router_nodes.clear()
        self.xtr_nodes.clear()
        self.msmr_nodes.clear()
        self.client_nodes.clear()
        self.graph.clear()
        # 重置迭代器
        self.next_subnet = iter(self.base_network.subnets(new_prefix=self.subnet_prefixlen))
        self.ip_allocator.reset()

    def get_status(self):
        status = {}
        for node in self.nodes:
            status[node.name] = node.get_status()
        return status

    def display_network_topology(self):
        node_count = len(self.nodes)

        # 根据节点数量动态调整布局参数，节点越多，k值越大，图片越大
        k_value = 0.5 + 0.1 * node_count  # 根据节点数量调整k值
        figsize = (12 + 0.2 * node_count, 8 + 0.2 * node_count)  # 动态调整图片尺寸

        plt.figure(figsize=figsize)  # 动态调整图像大小

        pos = nx.spring_layout(self.graph, k=k_value)  # 调整节点之间的距离

        # 定义节点颜色
        node_colors = []
        for node in self.nodes:
            if "xtr" in node.name.lower() or "ms" in node.name.lower():
                node_colors.append("#e599f7")
            elif "client" in node.name.lower():
                node_colors.append("#fcc2d7")
            else:
                node_colors.append("#a5d8ff")

        # 绘制节点，并显示其拥有的 IP 地址
        node_labels = {node.name: f"{node.name}\n" + "\n".join(f"{ip}" for net, ip in node.network_ips.items())
                       for node in self.nodes}
        nx.draw(self.graph, pos, with_labels=True, labels=node_labels, node_size=3000, node_color=node_colors,
                font_size=10, font_color="black", font_weight="bold")

        # 绘制边，并显示其网络名称
        edge_labels = {(edge[0], edge[1]): f'{self.networks[self.graph[edge[0]][edge[1]]["network"]]}'
                       for edge in self.graph.edges}
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels, font_color='red')

        # plt.tight_layout()  # 自动调整子图参数，使之填充整个图像区域
        # plt.show()
        plt.savefig(os.path.join(os.path.abspath(os.path.dirname(__file__)), '../output/topo.png'))

    def create_static_routes(self):
        """
        为每个节点创建静态路由，使得任意节点能够访问网络拓扑中的所有其他节点。
        对于相邻节点，不需要创建静态路由，因为它们已经在同一个网络中。
        """
        print('正在创建静态拓扑……')
        # 获取所有的节点
        nodes = []
        nodes.extend(self.router_nodes + self.xtr_nodes + self.msmr_nodes)
        # 创建线程池
        with ThreadPoolExecutor() as executor:
            futures = []
            # 遍历图中的每对节点，计算最短路径并配置静态路由
            for source_node in nodes:
                for target_node in nodes:
                    futures.append(
                        executor.submit(self.configure_route, source_node, target_node, nodes, self.graph,
                                        self.networks))
            # 等待所有任务完成
            for future in futures:
                future.result()

        print('静态路由创建完毕')

    @staticmethod
    def configure_route(source_node, target_node, nodes, graph, networks):
        if source_node != target_node:
            # 获取从 source_node 到 target_node 的最短路径
            path = nx.shortest_path(graph, source=source_node.name, target=target_node.name)

            # 遍历路径上的每个节点，配置静态路由
            for i in range(len(path) - 1):
                current_node_name = path[i]
                next_hop_node_name = path[i + 1]

                # 获取当前节点和下一跳节点的容器对象
                current_node = next(node for node in nodes if node.name == current_node_name)
                next_hop_node = next(node for node in nodes if node.name == next_hop_node_name)

                # 查找 current_node 和 next_hop_node 共享的网络
                common_networks = set(current_node.network_ips.keys()).intersection(
                    set(next_hop_node.network_ips.keys()))
                if common_networks:
                    network_name = common_networks.pop()  # 获取一个共享的网络名称

                    # 获取下一跳节点的 IP 地址
                    next_hop_ip = next_hop_node.network_ips[network_name]

                    for target_net in target_node.network_ips:
                        target_net = str(networks[target_net])
                        # 配置静态路由
                        cmd = f"ip route add {target_net} via {next_hop_ip}"
                        print(f'{current_node.name}({source_node.name}->{target_node.name}): {cmd}')
                        current_node.container.exec_run(cmd)

    def create_random_lisp_nodes(self, num_nodes, node_type):
        xtr_router_ips = {}
        lisp_nodes = []
        unused_routers = self.nodes[:]  # 初始所有路由器都未使用
        for i in range(num_nodes):
            node_name = f"{node_type}{i + 1}"
            lisp_node = LISPNode(node_name, self.ip_allocator, self.group_label, self.networks, node_type=node_type)
            network_name = self.create_network()  # 创建网络
            lisp_node.assign_ip(network_name)  # 为LISP节点分配IP

            # 优先选择未使用的路由器，如果没有未使用的路由器，则选择已使用的
            if unused_routers:
                connected_router = random.choice(unused_routers)
                unused_routers.remove(connected_router)
            else:
                connected_router = random.choice(self.nodes)

            connected_router.assign_ip(network_name)
            self.graph.add_edge(lisp_node.name, connected_router.name, network=network_name)  # 添加边并存储网络信息
            if node_type == "xTR":
                xtr_router_ips[node_name] = lisp_node.network_ips[network_name]  # 存储xtr的RLOC
            lisp_nodes.append(lisp_node)
        return lisp_nodes, xtr_router_ips

    def create_static_xtr_nodes(self, xtr_edges: list):
        """通过Router和xTR的关系，在Router的基础上创建xTR的节点与网络"""
        xtr_router_ips = {}
        xtr_nodes = []

        for edge in xtr_edges:
            router = None
            xtr_name = None
            for node_name in edge:  # 遍历edge，判断哪个是router
                node = self.get_node_by_name(node_name)
                if node:
                    router = node
                else:
                    xtr_name = node_name
            # 如果找到路由器且确定了 xTR 名称
            if router and xtr_name:
                # 使用 xtr_name 创建 xTR 节点
                xtr_node = LISPNode(xtr_name, self.ip_allocator, self.group_label, self.networks, node_type='xTR')
                # 创建网络并分配 IP
                network_name = self.create_network()
                xtr_node.assign_ip(network_name)
                router.assign_ip(network_name)
                # 添加边并记录网络信息
                self.graph.add_edge(xtr_node.name, router.name, network=network_name)
                xtr_router_ips[xtr_name] = xtr_node.network_ips[network_name]
                # 将 xTR 节点添加到列表
                xtr_nodes.append(xtr_node)
            else:
                raise ValueError("输入参数有误，缺少路由器或 xTR 名称")
        return xtr_nodes, xtr_router_ips


    def create_lisp_topology(self, num_xtr=2, num_msmr=1, xtr_edges=None):
        """
        插入LISP节点和端侧节点：
        - 插入指定数量的xTR节点和MSMR节点。
        - 为每个xTR节点分别连接一个客户端节点。
        :param num_xtr: xTR节点的数量
        :param num_msmr: MSMR节点的数量
        :param xtr_edges: 设置静态xTR拓扑，无视num_xtr配置
        """
        print('正在创建LISP节点……')
        # 创建xTR节点
        if xtr_edges:
            self.xtr_nodes, xtr_router_ips = self.create_static_xtr_nodes(xtr_edges)
        else:
            self.xtr_nodes, xtr_router_ips = self.create_random_lisp_nodes(num_xtr, "xTR")
        # 创建MSMR节点
        self.msmr_nodes, _ = self.create_random_lisp_nodes(num_msmr, "MSMR")
        # 获取MSMR节点的IP地址
        msmr_ips = [next(iter(msmr_node.network_ips.values())) for msmr_node in self.msmr_nodes]  # 获取所有MSMR节点的IP地址

        # 创建客户端节点并连接到xTR节点
        for i, xtr_node in enumerate(self.xtr_nodes):  # 直接根据xTR数量创建客户端节点
            client_node = ClientNode(f"Client{i + 1}", self.ip_allocator, self.group_label, self.networks)
            network_name = self.create_network()  # 为客户端和xTR节点创建网络
            client_node.assign_ip(network_name)
            xtr_node.assign_ip(network_name)
            client_node.default_ip = xtr_node.network_ips[network_name]
            self.graph.add_edge(client_node.name, xtr_node.name, network=network_name)  # 添加边并存储网络信息
            self.client_nodes.append(client_node)

            # 生成xTR节点的配置文件
            eid_prefix = str(self.networks[network_name])  # 客户端网络的前缀
            rloc_ip = xtr_router_ips[xtr_node.name]  # 获取xTR与路由节点相连一侧的IP地址
            xtr_node.generate_xtr_config_file(msmr_ips, eid_prefix, rloc_ip)

        # 获取所有xTR节点的eid_prefix
        eid_prefixes = [f"{self.networks[network_name]}"
                        for client_node in self.client_nodes for network_name in client_node.network_ips]
        # 为每个MSMR节点生成配置文件
        for msmr_node in self.msmr_nodes:
            msmr_node.generate_msmr_config_file(eid_prefixes)

        # 将所有LISP节点和端侧节点加入节点列表
        self.nodes.extend(self.xtr_nodes + self.msmr_nodes + self.client_nodes)
        print('LISP节点创建完毕')

    def create_lisp_topology_from_map(self, xtr_edges, xtr_eid_map, num_msmr=1):
        print('正在通过映射关系创建LISP节点……')
        self.xtr_nodes, xtr_router_ips = self.create_static_xtr_nodes(xtr_edges)
        self.msmr_nodes, _ = self.create_random_lisp_nodes(num_msmr, "MSMR")
        # 获取MSMR节点的IP地址
        msmr_ips = [next(iter(msmr_node.network_ips.values())) for msmr_node in self.msmr_nodes]  # 获取所有MSMR节点的IP地址

        # 创建客户端节点并连接到xTR节点
        for i, xtr_node in enumerate(self.xtr_nodes):  # 直接根据xTR数量创建客户端节点
            client_node = ClientNode(f"Client{i + 1}", self.ip_allocator, self.group_label, self.networks)
            xtr_simple_ip = xtr_eid_map.get(xtr_node.name)
            network_cidr = ipaddress.IPv4Network(xtr_simple_ip, strict=False)  # 转换为/24的网络
            network_name = self.create_manual_network(network_cidr)
            xtr_node.assign_ip_static(network_name, str(network_cidr.network_address + 2))  # 使用.2地址作为xtr地址
            client_node.assign_ip_static(network_name, str(network_cidr.network_address + 3))  # 使用.3地址作为client地址
            client_node.default_ip = xtr_node.network_ips[network_name]
            self.graph.add_edge(client_node.name, xtr_node.name, network=network_name)  # 添加边并存储网络信息
            self.client_nodes.append(client_node)

            # 生成xTR节点的配置文件
            eid_prefix = str(self.networks[network_name])  # 客户端网络的前缀
            rloc_ip = xtr_router_ips[xtr_node.name]  # 获取xTR与路由节点相连一侧的IP地址
            xtr_node.generate_xtr_config_file(msmr_ips, eid_prefix, rloc_ip)

        # 获取所有xTR节点的eid_prefix
        eid_prefixes = [f"{self.networks[network_name]}"
                        for client_node in self.client_nodes for network_name in client_node.network_ips]
        # 为每个MSMR节点生成配置文件
        for msmr_node in self.msmr_nodes:
            msmr_node.generate_msmr_config_file(eid_prefixes)

        # 将所有LISP节点和端侧节点加入节点列表
        self.nodes.extend(self.xtr_nodes + self.msmr_nodes + self.client_nodes)
        print('LISP节点创建完毕')

    def create_lisp_macvlan(self, num_msmr=1):
        print('正在创建lisp_macvlan节点……')
        # 读取macvlan配置
        config_dir = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), '../configs/macvlan_configs.json')  # 配置文件夹路径
        with open(config_dir, 'r') as file:
            config_list = json.load(file)['macvlan_configs']
            print(config_list)

        # 创建xTR节点
        self.xtr_nodes, xtr_router_ips = self.create_random_lisp_nodes(len(config_list), "xTR")
        # 创建MSMR节点
        self.msmr_nodes, _ = self.create_random_lisp_nodes(num_msmr, "MSMR")
        # 获取MSMR节点的IP地址
        msmr_ips = [next(iter(msmr_node.network_ips.values())) for msmr_node in self.msmr_nodes]  # 获取所有MSMR节点的IP地址

        eid_prefixes = []
        for i, xtr_config in enumerate(config_list):
            self.create_macvlan_network(
                net_name=xtr_config['netName'],
                parent=xtr_config['parent'],
                subnet=xtr_config['subnet'],
                gateway=xtr_config['gateway']
            )
            xtr_node = self.xtr_nodes[i]
            xtr_node.assign_ip_static(xtr_config['netName'], xtr_config['ip'])
            # 生成xTR节点的配置文件
            eid_prefix = xtr_config['subnet']  # 客户端网络的前缀
            eid_prefixes.append(eid_prefix)
            rloc_ip = xtr_router_ips[xtr_node.name]  # 获取xTR与路由节点相连一侧的IP地址
            xtr_node.generate_xtr_config_file(msmr_ips, eid_prefix, rloc_ip)

        # 为每个MSMR节点生成配置文件
        for msmr_node in self.msmr_nodes:
            msmr_node.generate_msmr_config_file(eid_prefixes)

        # 将所有LISP节点和端侧节点加入节点列表
        self.nodes.extend(self.xtr_nodes + self.msmr_nodes)
        print('lisp_macvlan节点创建完毕')

    @staticmethod
    def cleanup_config_files():
        """清理指定配置文件夹中的所有配置文件"""
        print('开始清理配置文件……')
        config_dir_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../output')
        if os.path.exists(config_dir_path):
            config_files = glob.glob(os.path.join(config_dir_path, '*.conf'))
            log_files = glob.glob(os.path.join(config_dir_path, '*.log'))
            all_files = config_files + log_files
            for file_path in all_files:
                os.remove(file_path)
        print('清理配置文件完毕')

    def get_pair_delay_by_name(self, src_node_name, dst_node_name, count=1):
        src_node = self.get_node_by_name(src_node_name)
        dst_node = self.get_node_by_name(dst_node_name)
        return self.get_pair_delay(src_node, dst_node, count)

    @staticmethod
    def get_pair_delay(src_node, dst_node, count=1):
        if src_node and dst_node:
            src_ip = list(src_node.network_ips.values())[0]
            dst_ip = list(dst_node.network_ips.values())[0]
            res = src_node.ping(dst_ip, count)
            js = {'src_node': src_node.name, 'dst_node': dst_node.name, 'src_ip': src_ip, 'dst_ip': dst_ip}
            js = {**res, **js}
            print(f'-> ping {src_node.name}->{dst_node.name}：{js}')
            # print(routing_path.traceroute('xtr_1', dst_ip))
            return js
        else:
            return None

    def get_pair_traceroute(self, src_node, dst_node):
        if src_node and dst_node:
            src_ip = list(src_node.network_ips.values())[0]
            dst_ip = list(dst_node.network_ips.values())[0]
            res = src_node.trace_route_path(dst_ip=dst_ip)
            # 构建路径中的节点名称列表
            route_path = []
            for hop in res:
                ip_address = hop.get('ip')
                node_name = self.get_node_name_by_ip(ip_address) if ip_address != '*' else '*'
                route_path.append(node_name)
            js = {'src_node': src_node.name, 'dst_node': dst_node.name,
                  'src_ip': src_ip, 'dst_ip': dst_ip, 'route_path': route_path}
            print(f'-> traceroute {src_node.name}->{dst_node.name}：{js}')
            return js
        else:
            return None

    def parse_route_path(self, traceroute_res):
        route_path = []
        for hop in traceroute_res:
            ip_address = hop.get('ip')
            node_name = self.get_node_name_by_ip(ip_address) if ip_address != '*' else '*'
            route_path.append(node_name)
        return route_path

    def ping_all(self, count=1):
        results = []
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.get_pair_delay, *pair, count)
                       for pair in combinations(self.xtr_nodes, 2)]
            for future in futures:
                # 使用 future.result() 获取每个任务的返回值
                results.append(future.result())
        return results

    def traceroute_all(self):
        results = []
        # with ThreadPoolExecutor() as executor:
        #     futures = [executor.submit(self.get_pair_traceroute, *pair)
        #                for pair in combinations(self.xtr_nodes, 2)]
        #     for future in futures:
        #         # 使用 future.result() 获取每个任务的返回值
        #         results.append(future.result())
        for pair in combinations(self.xtr_nodes, 2):
            results.append(self.get_pair_traceroute(*pair))
            sleep(1)
        return results

    def get_node_by_name(self, node_name) -> Optional[Union[Node, RouterNode, LISPNode, ClientNode]]:
        return next((node for node in self.nodes if node.name == node_name), None)

    def get_node_name_by_ip(self, node_ip):
        """根据 IP 获取节点名称"""
        for node in self.nodes:
            ips = list(node.network_ips.values())
            if node_ip in ips:
                return node.name
        return None

    def get_topo(self):
        nodes = []
        for node in self.nodes:
            nodes.append({"name": node.name, "type": node.node_type, "coordinates": node.coordinates})
        edges = list(self.graph.edges())
        return {"nodes": nodes, "edges": edges}

    def apply_tc_on_edges(self, edges, delay=None, jitter=None, loss=None, max_queue_size=None):
        """
        为拓扑中的每条边应用 tc 规则
        :param edges: 边的列表，每个边表示为 (节点1, 节点2)
        :param delay: 设置的延迟（例如 "100ms"）
        :param jitter: 设置的抖动（例如 "10ms"）
        :param loss: 丢包率（例如 0.1 表示 0.1% 的丢包率）
        :param max_queue_size: 最大队列长度（例如 1000）
        """
        print('正在应用tc规则……')
        for edge in edges:
            assert edge in self.graph.edges, f"边 {edge} 不在图中"
            network_name = self.graph.edges[edge]['network']

            for node_name in edge:
                node: RouterNode = self.get_node_by_name(node_name)
                assert node, f"节点 {node_name} 不存在"
                interface = node.get_interface_by_network(str(self.networks[network_name]))
                assert interface, f"节点 {node_name} 没有找到网络 {network_name} 的接口"
                node.apply_tc_delay(interface=interface,
                                    delay=delay, jitter=jitter, loss=loss, max_queue_size=max_queue_size)
        print('应用tc规则完毕')

    def control_nodes_network(self, node_name_list, deactivate=False):
        for node_name in node_name_list:
            node = self.get_node_by_name(node_name)
            if deactivate:
                node.disconnect_all_net()
                print(f'节点{node_name}已离线')
            else:
                node.connect_all_net()
                print(f'节点{node_name}已上线')
