import ipaddress


class IPAddressAllocator:
    def __init__(self):
        self.available_ips = {}
        self.used_ips = {}

    def add_network(self, network_cidr: ipaddress.IPv4Network):
        """添加新网络并初始化 IP 地址池"""
        # 获取所有可用 IP 地址并排除 .1 地址（docker bridge ip）
        available_ips = set(network_cidr.hosts())
        excluded_ip = network_cidr.network_address + 1  # .1 地址
        if excluded_ip in available_ips:
            available_ips.remove(excluded_ip)

        self.available_ips[str(network_cidr)] = available_ips
        self.used_ips[str(network_cidr)] = set()

    def allocate_ip(self, network_cidr: ipaddress.IPv4Network):
        """为指定网络分配一个 IP 地址"""
        network_cidr = str(network_cidr)
        if not self.available_ips[network_cidr]:
            raise ValueError(f"No available IP addresses in network {network_cidr}")
        ip = self.available_ips[network_cidr].pop()
        self.used_ips[network_cidr].add(ip)
        return str(ip)

    def release_ip(self, network_cidr: ipaddress.IPv4Network, ip):
        """释放指定网络的 IP 地址"""
        network_cidr = str(network_cidr)
        ip = ipaddress.ip_address(ip)
        if ip in self.used_ips[network_cidr]:
            self.used_ips[network_cidr].remove(ip)
            self.available_ips[network_cidr].add(ip)

    def reset(self):
        """重置 IP 池"""
        self.available_ips = {}
        self.used_ips = {}
