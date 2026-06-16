import ipaddress
from time import sleep
from src.network_simulation import NetworkSimulation
from src.nodes import LISPNode, RouterNode


def movement(ns: NetworkSimulation):
    xtr_2: LISPNode = ns.get_node_by_name('xtr_2')
    node_2: RouterNode = ns.get_node_by_name('node_2')
    xtr_2.container.stop()
    node_2.container.stop()

    # 创建新网络
    print('创建新网络')
    new_net_name = ns.create_network()

    # xtr2离开原网络
    ip_xtr2 = ipaddress.ip_address(xtr_2.rloc_ip)
    print(f'-> old RLOC：{ip_xtr2}')
    old_net_name = None
    for net_name, subnet in ns.networks.items():
        if ip_xtr2 in subnet:
            old_net_name = net_name
    if not old_net_name:
        return
    xtr_2.disconnect_net(old_net_name)

    # 加入新网络
    print('-> 为xtr2注册新网络')
    xtr_2.assign_ip(new_net_name)
    new_ip_xtr2 = xtr_2.network_ips.get(new_net_name)
    xtr_2.connect_net(new_net_name, new_ip_xtr2)
    print('-> 为node2注册新网络')
    node_2.assign_ip(new_net_name)
    new_ip_node2 = node_2.network_ips.get(new_net_name)
    node_2.connect_net(new_net_name, new_ip_node2)

    # 修改配置
    print('-> 更新xtr2配置')
    xtr_2.generate_xtr_config_file(rloc_ip=new_ip_xtr2)


def main():
    """将xtr2从node3迁移至node2"""
    ns = NetworkSimulation()
    ns.cleanup()
    ns.create_circle_nodes(5)
    ns.create_lisp_topology(xtr_edges=[["node_1", "xtr_1"], ["node_3", "xtr_2"]], num_msmr=1)
    ns.display_network_topology()
    ns.start_simulation()

    xtr_1: LISPNode = ns.get_node_by_name('xtr_1')
    xtr_2: LISPNode = ns.get_node_by_name('xtr_2')
    node_2: RouterNode = ns.get_node_by_name('node_2')

    add = 0
    while True:
        print(f'ENV: {add * 10}s')
        if add == 5:
            print('启动移动事件')
            movement(ns)
            print('移动完毕，待启动')
        elif add == 10:
            print('启动节点')
            xtr_2.start()
            node_2.start()

        if not 5 <= add < 10:
            ns.get_pair_delay_by_name('Client1', 'Client2')
            print(f'-> route_path: {ns.parse_route_path(xtr_1.trace_route_path(xtr_2.rloc_ip))}')
        add += 1
        sleep(10)


if __name__ == '__main__':
    main()