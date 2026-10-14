from src.network_simulation import NetworkSimulation


def main():
    network_simulation = NetworkSimulation()
    network_simulation.cleanup()
    network_simulation.create_circle_nodes(5)
    network_simulation.create_lisp_topology(xtr_edges=[["node_1", "xtr_1"], ["node_3", "xtr_2"]], num_msmr=1)
    network_simulation.display_network_topology()
    network_simulation.start_simulation()


if __name__ == "__main__":
    main()
