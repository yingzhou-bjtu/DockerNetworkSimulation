from time import sleep
from src.network_simulation import NetworkSimulation

def main():
    """节点故障恢复测试"""
    ns = NetworkSimulation()
    ns.cleanup()
    ns.create_circle_nodes(5)
    ns.create_lisp_topology(xtr_edges=[["node_1", "xtr_1"], ["node_3", "xtr_2"]], num_msmr=1)
    ns.display_network_topology()
    ns.start_simulation()

    add = 0
    node_2 = ns.get_node_by_name('node_2')
    while True:
        sleep(10)
        ns.ping_all()
        ns.traceroute_all()
        if add == 5:
            print('停止node_2')
            node_2.container.stop()
        elif add == 10:
            print('启动node_2')
            node_2.start()

        add += 1
        print(f'ENV: {add * 10}s')

if __name__ == "__main__":
    main()