from time import sleep
from src.network_simulation import NetworkSimulation

if __name__ == "__main__":
    network_simulation = NetworkSimulation()
    network_simulation.cleanup()
    # network_simulation.create_random_nodes(10)
    network_simulation.create_circle_nodes(5)
    # network_simulation.create_grid_nodes(12, 12)
    # my_nodes = ["node_1", "node_2", "node_3", "node_4"]
    # my_edges = [["node_1", "node_2"], ["node_2", "node_3"], ["node_3", "node_4"]]
    # network_simulation.create_custom_topology(my_nodes, my_edges)
    network_simulation.create_lisp_topology(xtr_edges=[["node_1", "xtr_1"], ["node_3", "xtr_2"]], num_msmr=1)

    # network_simulation.create_lisp_topology_from_map(
    #     xtr_edges=[["node_1", "xtr_1"], ["node_2", "xtr_2"], ["node_3", "xtr_3"],
    #                ["node_4", "xtr_4"], ["node_5", "xtr_5"], ["node_6", "xtr_6"],
    #                ["node_7", "xtr_7"], ["node_8", "xtr_8"], ["node_9", "xtr_9"]],
    #     xtr_eid_map={"xtr_1": "10.11.0.0/24", "xtr_2": "10.11.1.0/24","xtr_3": "10.11.2.0/24",
    #                  "xtr_4": "10.11.3.0/24","xtr_5": "10.11.4.0/24","xtr_6": "10.11.5.0/24",
    #                  "xtr_7": "10.11.6.0/24","xtr_8": "10.11.7.0/24","xtr_9": "10.11.8.0/24"},
    #     num_msmr=1
    # )
    network_simulation.display_network_topology()
    network_simulation.start_simulation()

    add = 0
    while True:
        sleep(10)
        network_simulation.ping_all()
        network_simulation.traceroute_all()
        if add == 5:
            # network_simulation.control_nodes_network(['node_2'], deactivate=True)
            node_2 = network_simulation.get_node_by_name('node_2')
            print('停止node_2')
            node_2.container.stop()
        elif add == 10:
            # network_simulation.control_nodes_network(['node_2'])
            print('启动node_2')
            node_2.start()

        add += 1
        print(f'ENV: {add*10}s')

    # network_simulation.create_static_routes()
    # network_simulation.apply_tc_on_edges(edges=my_edges, delay='100ms', jitter='50ms')
    # print(network_simulation.get_pair_delay('xTR1', 'xTR2'))
