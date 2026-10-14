import math
import os
import re

from .docker_backend import create_docker_client


class Node:
    """通用节点基类，包含IP地址管理和Docker容器的基本操作"""

    def __init__(self, name, ip_allocator, group_label, networks, docker_client=None):
        self.name = name
        self.network_ips = {}  # 用于存储每个网络的 IP 地址，network_name-ip
        self.container = None
        self.ip_allocator = ip_allocator
        self.group_label = group_label
        self.networks = networks
        self.coordinates = {"latitude": 0.0, "longitude": 0.0}
        self._client = docker_client

    @property
    def client(self):
        if self._client is None:
            self._client = create_docker_client()
        return self._client

    def assign_ip(self, network_name):
        """为节点分配指定网络的 IP 地址"""
        network_cidr = str(self.networks[network_name])
        ip_address = self.ip_allocator.allocate_ip(network_cidr)
        self.network_ips[network_name] = ip_address

    def assign_ip_static(self, network_name, ip_address):
        self.network_ips[network_name] = ip_address

    def release_ip(self, network_name):
        network_cidr = str(self.networks[network_name])
        ip_address = self.network_ips.get(network_name)
        self.ip_allocator.release_ip(network_cidr, ip_address)
        self.network_ips.pop(network_name)

    def release_ips(self):
        """释放节点分配的所有 IP 地址"""
        for network_name, ip_address in self.network_ips.items():
            network_cidr = str(self.networks[network_name])
            self.ip_allocator.release_ip(network_cidr, ip_address)
        self.network_ips.clear()

    def start(self):
        """启动节点容器"""
        raise NotImplementedError("子类必须实现此方法")

    def stop(self):
        """停止并删除容器"""
        if self.container:
            self.container.stop()
            self.container.remove()
            self.release_ips()
            print(f"-> 容器{self.name}停止成功")

    def get_status(self):
        """获取容器状态"""
        if self.container:
            self.container.reload()
            return self.container.status
        return "stopped"

    def get_ip_addr(self):
        """获取容器ip addr"""
        ip_addr = self.container.exec_run("ip addr", detach=False).output.decode('utf-8')
        # print(f"{self.name}:\n{ip_addr.output.decode('utf-8')}")  # 打印当前的路由配置
        # 定义正则表达式匹配接口信息
        iface_pattern = re.compile(r'^\d+:\s+(\S+):')  # 匹配接口名称
        inet_pattern = re.compile(r'inet\s+(\S+)')  # 匹配IPv4地址
        inet6_pattern = re.compile(r'inet6\s+(\S+)')  # 匹配IPv6地址

        interfaces = {}
        current_iface = None

        # 逐行解析输出
        for line in ip_addr.splitlines():
            iface_match = iface_pattern.match(line)
            if iface_match:
                # 找到一个新的接口
                current_iface = iface_match.group(1)
                interfaces[current_iface] = {'inet': [], 'inet6': []}
            elif current_iface:
                # 匹配IPv4地址
                inet_match = inet_pattern.search(line)
                if inet_match:
                    interfaces[current_iface]['inet'].append(inet_match.group(1))
                # 匹配IPv6地址
                inet6_match = inet6_pattern.search(line)
                if inet6_match:
                    interfaces[current_iface]['inet6'].append(inet6_match.group(1))

        return interfaces

    def get_ip_route(self):
        ip_route = self.container.exec_run("ip route", detach=False).output.decode('utf-8')
        # 定义正则表达式匹配路由信息
        route_pattern = re.compile(
            r'(?P<destination>\S+)\s+'
            r'(via\s+(?P<gateway>\S+)\s+)?'
            r'dev\s+(?P<interface>\S+)\s+'
            r'(proto\s+(?P<proto>\S+)\s+)?'
            r'(scope\s+(?P<scope>\S+)\s+)?'
            r'(src\s+(?P<src>\S+)\s+)?'
            r'(metric\s+(?P<metric>\d+))?'
        )

        routes = []

        # 逐行解析输出
        for line in ip_route.splitlines():
            match = route_pattern.match(line)
            if match:
                route_info = match.groupdict()
                # 删除值为None的键
                route_info = {k: v for k, v in route_info.items() if v is not None}
                routes.append(route_info)

        return routes

    def ping(self, dst_ip, pkg_count=3):
        # 使用 ping 测量网络时延
        ping_result = self.container.exec_run(f'sh -c "LANG=C ping -c{pkg_count} {dst_ip}"')
        output = ping_result.output.decode()

        # 提取时延和丢包率
        delay_pattern = r'(?<=time=)(\d+\.\d+)'
        packet_loss_pattern = r'(\d+)% packet loss'

        delays = re.findall(delay_pattern, output)
        packet_loss = re.search(packet_loss_pattern, output)
        loss_rate = round(float(packet_loss.group(1)), 3) if packet_loss else None

        if delays:
            delays = [float(d) for d in delays]
            min_delay = min(delays)
            avg_delay = sum(delays) / len(delays)
            max_delay = max(delays)
            mdev = math.sqrt(sum((x - avg_delay) ** 2 for x in delays) / len(delays))  # 网络抖动
        else:
            min_delay = avg_delay = max_delay = mdev = 0

        return {'loss_rate': loss_rate, 'avg_delay': avg_delay, 'min_delay': min_delay,
                'max_delay': max_delay, 'mdev': mdev, 'pkg_count': pkg_count}

    def trace_route_path(self, dst_ip, src_ip=None, max_hops=30):
        """
        使用 traceroute 测量网络路径和每一跳的时延。

        Args:
        - dst_ip (str): 目标 IP 地址。
        - src_ip (str): 源 IP 地址（可选）。
        - max_hops (int): 最大跳数（默认 30）。

        Returns:
        - list: 包含路径中每一跳节点名称。
        """
        # 构建 traceroute 命令
        src_option = f"-s {src_ip}" if src_ip else ""
        trace_result = self.container.exec_run(f'sh -c "LANG=C '
                                               f'traceroute -n -m {max_hops} {src_option} {dst_ip}"', detach=False)
        output = trace_result.output.decode()
        # 提取每一跳的 IP 和时延信息
        hop_pattern = r"^\s*(\d+)\s+([\d.]+)\s+(\d+\.\d+) ms(?:\s+(\d+\.\d+) ms\s+(\d+\.\d+) ms)?"
        hops = []
        for line in output.splitlines():
            match = re.search(hop_pattern, line)
            if match:
                hop_number = int(match.group(1))
                ip_address = match.group(2)
                delay_values = [float(d) for d in match.groups()[2:] if d]  # 提取时延数值

                # 计算每一跳的最小、最大、平均时延
                min_delay = min(delay_values)
                avg_delay = sum(delay_values) / len(delay_values)
                max_delay = max(delay_values)
                mdev = math.sqrt(sum((x - avg_delay) ** 2 for x in delay_values) / len(delay_values))

                hops.append({
                    'hop': hop_number,
                    'ip': ip_address,
                    'min_delay': min_delay,
                    'avg_delay': avg_delay,
                    'max_delay': max_delay,
                    'mdev': mdev,
                })
            else:
                # 跳数信息丢失的情况
                if "*" in line:
                    hops.append({
                        'hop': len(hops) + 1,
                        'ip': '*',
                        'min_delay': None,
                        'avg_delay': None,
                        'max_delay': None,
                        'mdev': None,
                    })
        return hops

    def apply_tc_delay(self, interface, delay=None, jitter=None, loss=None, max_queue_size=None):
        """
        应用 tc netem 命令，为网络接口设置时延、抖动、丢包率和队列大小。

        参数:
        - container: Docker 容器对象
        - interface: 容器内的网络接口名称
        - delay: 设置的延迟（例如 "100ms"）
        - jitter: 设置的抖动（例如 "10ms"）
        - loss: 丢包率（例如 0.1 表示 0.1% 的丢包率）
        - max_queue_size: 最大队列长度（例如 1000）
        """
        if delay is not None and not isinstance(delay, str):
            raise ValueError(f"无效的 delay 参数: {delay}, 需要是字符串")
        if jitter is not None and not isinstance(jitter, str):
            raise ValueError(f"无效的 jitter 参数: {jitter}, 需要是字符串")
        if loss is not None and (not isinstance(loss, float) or not 0 <= loss <= 100):
            raise ValueError(f"无效的丢包率: {loss}, 必须是 0 到 100 之间的浮点数")
        if max_queue_size is not None and (not isinstance(max_queue_size, int) or max_queue_size <= 0):
            raise ValueError(f"无效的队列大小: {max_queue_size}, 必须是正整数")

        # 构建 tc netem 命令的参数部分
        netem_args = []

        if delay:
            netem_args.append(f"delay {delay}")
            if jitter:
                netem_args.append(jitter)
        if loss:
            netem_args.append(f"loss {loss}%")
        if max_queue_size:
            netem_args.append(f"limit {max_queue_size}")

        # 构建最终的 tc 命令
        if netem_args:
            self.container.exec_run(f"tc qdisc del dev {interface} root")  # 尝试删除可能存在的旧tc规则
            netem_command = f"tc qdisc add dev {interface} root netem " + ' '.join(netem_args)
            exec_log = self.container.exec_run(netem_command)

            # 检查命令是否成功执行
            if exec_log.exit_code != 0:
                raise Exception(f"应用 tc 命令失败: {exec_log.output.decode()}")
            else:
                print(f"{self.name}/{interface}：{netem_command}")
        else:
            print("没有指定网络条件，未执行任何 tc 命令")

    def get_interface_by_network(self, network):
        network = network.replace('/', '\\/')
        text = f"ip route | awk '/{network}/ {{print $3}}'"
        result: str = self.container.exec_run(f'sh -c "{text}"').output.decode('utf-8')
        return result.strip()

    def connect_net(self, network_name, ip_address):
        self.client.networks.get(network_name).connect(self.container, ipv4_address=ip_address)

    def connect_all_net(self):
        for network_name, ip_address in self.network_ips.items():
            self.client.networks.get(network_name).connect(self.container, ipv4_address=ip_address)
                                                           # driver_opt={"com.docker.network.endpoint.ifname": f"e{ip_address}"})
    def disconnect_net(self, network_name):
        self.client.networks.get(network_name).disconnect(self.container)

    def disconnect_all_net(self):
        for network_name, ip_address in self.network_ips.items():
            self.client.networks.get(network_name).disconnect(self.container)


class RouterNode(Node):
    """路由设备类，继承自Node类，表示传统路由器节点"""

    def __init__(self, name, ip_allocator, group_label, networks):
        super().__init__(name, ip_allocator, group_label, networks)  # 调用基类的构造函数
        self.node_type = "Router"

    def start(self):
        if self.container:  # 如果已启动过该容器
            if self.container.status != "running":
                print(f"容器 {self.name} 已存在，但未运行。")
                self.container.start()
        else:
            self.container = self.client.containers.run(
                "aio",
                name=self.name,
                detach=True,
                tty=True,
                command="sh -c 'touch /app/ospf/ospf.log && tail -f /app/ospf/ospf.log'",
                labels={"group": self.group_label},
                cap_add=["NET_ADMIN", "NET_RAW"]
            )
            self.connect_all_net()
        try:
            self.client.networks.get("bridge").disconnect(self.container)  # 从默认桥接网络退出
        except Exception as e:
            print(e)
        self.container.exec_run("ip r del default", detach=False)
        self.container.exec_run("sh -c '/app/ospf/ospf >> /app/ospf/ospf.log 2>&1'", detach=True)
        print(f"-> 容器{self.name}启动成功")


class FrrOSPFRouterNode(Node):
    """Frr OSPF路由类，继承自Node类"""

    def __init__(self, name, ip_allocator, group_label, networks):
        super().__init__(name, ip_allocator, group_label, networks)  # 调用基类的构造函数
        self.node_type = "Router"
        self.frr_config_file = None  # frr配置文件路径
        self.vtysh_config_file = None  # vtysh配置文件路径

    def generate_frr_config_file(self):
        """动态生成FRR OSPF配置文件"""
        config_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../output')  # 配置文件夹路径
        os.makedirs(config_dir, exist_ok=True)  # 如果文件夹不存在，则创建

        self.frr_config_file = os.path.join(config_dir, f"{self.name}_frr.conf")  # frr配置文件路径
        with open(self.frr_config_file, 'w') as config:
            config_content = (
                "router ospf\n"
                " network 0.0.0.0/0 area 0.0.0.0\n"
                "log file /var/log/frr/frr.log\n"
            )
            config.write(config_content)

        self.vtysh_config_file = os.path.join(config_dir, f"{self.name}_vtysh.conf")  # vtysh配置文件路径
        with open(self.vtysh_config_file, 'w') as config:
            config_content = (
                "service integrated-vtysh-config\n"
            )
            config.write(config_content)

    def start(self):
        self.generate_frr_config_file()  # 生成配置文件

        self.container = self.client.containers.run(
            "frr",
            name=self.name,
            detach=True,
            tty=True,
            command="sh -c 'touch /var/log/frr/frr.log && tail -f /var/log/frr/frr.log'",
            labels={"group": self.group_label},
            cap_add=["NET_ADMIN", "NET_RAW", "SYS_ADMIN"],
            # cap_add=["NET_ADMIN", "NET_RAW"],
            volumes={
                self.frr_config_file: {'bind': '/etc/frr/frr.conf', 'mode': 'ro'},  # 绑定配置文件到容器
                self.vtysh_config_file: {'bind': '/etc/frr/vtysh.conf', 'mode': 'ro'}
            },
        )
        self.connect_all_net()
        try:
            self.client.networks.get("bridge").disconnect(self.container)  # 从默认桥接网络退出
        except Exception as e:
            print(e)

        self.container.exec_run("ip r del default", detach=False)
        self.container.exec_run("sh -c \"sed -i 's/^ospfd=no$/ospfd=yes/' /etc/frr/daemons\"", detach=False)  # 开启ospfd
        self.container.exec_run("sh -c '/usr/lib/frr/frrinit.sh start'", detach=True)
        print(f"-> 容器{self.name}启动成功")


class LISPNode(Node):
    """LISP节点类，继承自Node类，用于实现LISP功能节点（xTR、MSMR等）"""

    def __init__(self, name, ip_allocator, group_label, networks, node_type):
        super().__init__(name, ip_allocator, group_label, networks)
        self.node_type = node_type  # 配置文件类型，例如 xTR 或 MSMR
        self.config_file = None  # 配置文件路径

        self.msmr_ips = None
        self.eid_prefix = None
        self.rloc_ip = None

    def generate_xtr_config_file(self, msmr_ips=None, eid_prefix=None, rloc_ip=None):
        """动态生成LISP配置文件，支持多个MSMR节点"""
        if msmr_ips :
            self.msmr_ips = msmr_ips
        if eid_prefix:
            self.eid_prefix = eid_prefix
        if rloc_ip:
            self.rloc_ip = rloc_ip

        config_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../output')  # 配置文件夹路径
        os.makedirs(config_dir, exist_ok=True)  # 如果文件夹不存在，则创建

        self.config_file = os.path.join(config_dir, f"{self.name}.conf")  # 配置文件路径

        # 构建 map-resolver 和 map-server 块
        map_resolver_block = ""
        map_server_block = ""
        for msmr_ip in self.msmr_ips:
            map_resolver_block += (
                "map-resolver = {\n"
                f"    {msmr_ip}\n"
                "}\n"
            )
            map_server_block += (
                "map-server {\n"
                f"    address        = {msmr_ip}\n"
                "    key-type       = 1\n"
                "    key            = password\n"
                "    proxy-reply    = off\n"
                "}\n"
            )
        config_content = (
                "debug                  = 1\n"
                "map-request-retries    = 2\n"
                "log-file               = /var/log/oor.log\n"
                "ipv6-scope             = SITE\n"
                f"operating-mode         = {self.node_type}\n"
                "encapsulation          = LISP\n"
                "nat_traversal_support  = off\n"
                "rloc-probing {\n"
                "    rloc-probe-interval = 0\n"
                "}\n"
                + map_resolver_block +
                map_server_block +
                "database-mapping {\n"
                f"    eid-prefix     = {self.eid_prefix}\n"
                "    iid            = 0\n"
                "    ttl            = 10\n"
                "    rloc-address {\n"
                f"        address    = {self.rloc_ip}\n"
                "        priority   = 1\n"
                "        weight     = 100\n"
                "    }\n"
                # "   rloc-iface {\n"
                # "       interface  = eth1\n"
                # "       ip_version = 4\n"
                # "       priority   = 2\n"
                # "       weight     = 1\n"
                # "   }\n"
                # "}\n"
        )

        # 写入配置文件
        with open(self.config_file, 'w') as config:
            config.write(config_content)

    def generate_msmr_config_file(self, eid_prefixes):
        """动态生成MSMR配置文件，支持多个xTR节点的EID前缀"""
        config_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../output')  # 配置文件夹路径
        os.makedirs(config_dir, exist_ok=True)  # 如果文件夹不存在，则创建

        self.config_file = os.path.join(config_dir, f"{self.name}.conf")  # 配置文件路径

        # 构建 lisp-site 块
        lisp_site_blocks = ""
        for eid_prefix in eid_prefixes:
            lisp_site_blocks += (
                "lisp-site {\n"
                f"    eid-prefix            = {eid_prefix}\n"
                "    key-type              = 1\n"
                "    key                   = password\n"
                "    iid                   = 0\n"
                "    accept-more-specifics = true\n"
                "}\n"
            )

        config_content = (
                "debug                  = 3\n"
                "map-request-retries    = 2\n"
                "log-file               = /var/log/oor.log\n"
                "ipv6-scope             = SITE\n"
                "operating-mode         = MS\n"
                "control-iface          = eth1\n"
                + lisp_site_blocks
        )

        # 写入配置文件
        with open(self.config_file, 'w') as config:
            config.write(config_content)

    def start(self):
        """启动LISP节点容器，并加载LISP配置文件"""
        if self.container:  # 如果已启动过该容器
            if self.container.status != "running":
                print(f"容器 {self.name} 已存在，但未运行。")
                self.container.start()
        else:
            self.container = self.client.containers.run(
                "aio",  # 使用指定的OOR镜像
                name=self.name,
                detach=True,
                tty=True,
                command="sh -c 'touch /app/ospf/ospf.log /app/lisp/lisp.log && "
                        "tail -f /app/ospf/ospf.log /app/lisp/lisp.log'",
                labels={"group": self.group_label},
                cap_add=["NET_ADMIN", "NET_RAW"],
                sysctls={
                    "net.ipv4.conf.default.rp_filter": "0",
                    "net.ipv4.conf.all.rp_filter": "0",
                    "net.ipv4.ip_forward": "1",
                    "net.ipv6.conf.all.forwarding": "1",
                    "net.ipv6.conf.all.disable_ipv6": "0"
                },
                volumes={
                    self.config_file: {'bind': '/oor/oor.conf', 'mode': 'ro'}  # 绑定配置文件到容器
                },
                devices=["/dev/net/tun:/dev/net/tun"]  # 添加设备参数
            )
            # 连接到指定的多个网络
            self.connect_all_net()
        try:
            self.client.networks.get("bridge").disconnect(self.container)  # 从默认桥接网络退出
        except Exception as e:
            print(e)
        self.container.exec_run("ip r del default", detach=False)
        self.container.exec_run("sh -c 'oor -f /oor/oor.conf >> /app/lisp/lisp.log 2>&1'", detach=True)
        self.container.exec_run("sh -c '/app/ospf/ospf >> /app/ospf/ospf.log 2>&1'", detach=True)
        print(f"-> 容器{self.name}启动成功")


class ClientNode(Node):
    """端侧节点类，继承自Node类，表示用户设备"""

    def __init__(self, name, ip_allocator, group_label, networks):
        super().__init__(name, ip_allocator, group_label, networks)  # 调用基类的构造函数
        self.node_type = "Client"
        self.default_ip = None

    def start(self):
        mapping_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../output/forward_targets.json')
        self.container = self.client.containers.run(
            "aio",
            name=self.name,
            detach=True,
            tty=True,
            command="sh -c 'touch /app/socket/udp_forward.log && tail -f /app/socket/udp_forward.log'",
            labels={"group": self.group_label},
            volumes={
                mapping_path: {'bind': '/app/socket/forward_targets.json', 'mode': 'ro'}  # 绑定配置文件到容器
            },
            cap_add=["NET_ADMIN", "NET_RAW"]
        )
        self.connect_all_net()
        try:
            self.client.networks.get("bridge").disconnect(self.container)  # 从默认桥接网络退出
        except Exception as e:
            print(e)
        self.container.exec_run("ip r del default", detach=False)
        self.container.exec_run(f"ip r add default via {self.default_ip}", detach=False)
        self.container.exec_run("sh -c 'stdbuf -oL /app/socket/udp_forward 5132 1235 1 "
                                "> /app/socket/udp_forward.log 2>&1'", detach=True)
        print(f"-> 容器{self.name}启动成功")
