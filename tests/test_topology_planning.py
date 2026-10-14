import random

from src.network_simulation import NetworkSimulation
from src.topology import circle_router_topology, grid_router_topology, random_router_topology


class FakeNetwork:
    def __init__(self, name):
        self.name = name
        self.removed = False

    def remove(self):
        self.removed = True


class MemoryNetworkBackend:
    def __init__(self):
        self.bridge_networks = []
        self.macvlan_networks = []
        self.containers = []
        self.group_networks = []

    def list_group_containers(self):
        return list(self.containers)

    def list_group_networks(self):
        return list(self.group_networks)

    def stop_and_remove_container(self, container):
        container.stop()
        container.remove()

    def create_bridge_network(self, net_name, subnet):
        self.bridge_networks.append((net_name, str(subnet)))
        return FakeNetwork(net_name)

    def create_macvlan_network(self, net_name, parent, subnet, gateway):
        self.macvlan_networks.append((net_name, parent, str(subnet), str(gateway)))
        return FakeNetwork(net_name)


def test_circle_topology_planner_has_expected_ring_edges():
    nodes, edges = circle_router_topology(4)

    assert [node["name"] for node in nodes] == ["node_1", "node_2", "node_3", "node_4"]
    assert edges == [
        ("node_1", "node_2"),
        ("node_2", "node_3"),
        ("node_3", "node_4"),
        ("node_4", "node_1"),
    ]


def test_grid_topology_planner_splits_node_layout_from_network_creation():
    nodes, edges = grid_router_topology(2, 3)

    assert [node["name"] for node in nodes] == [
        "node_1",
        "node_2",
        "node_3",
        "node_4",
        "node_5",
        "node_6",
    ]
    assert edges == [
        ("node_1", "node_2"),
        ("node_1", "node_4"),
        ("node_2", "node_3"),
        ("node_2", "node_5"),
        ("node_3", "node_6"),
        ("node_4", "node_5"),
        ("node_5", "node_6"),
    ]


def test_random_topology_planner_is_deterministic_with_seeded_rng():
    nodes, edges = random_router_topology(4, rng=random.Random(7))

    assert [node["name"] for node in nodes] == ["node_1", "node_2", "node_3", "node_4"]
    assert edges == [
        ("node_1", "node_2"),
        ("node_1", "node_3"),
        ("node_1", "node_4"),
        ("node_2", "node_4"),
    ]


def test_network_simulation_uses_injected_network_backend_for_topology_state():
    backend = MemoryNetworkBackend()
    simulation = NetworkSimulation(docker_backend=backend)

    simulation.create_grid_nodes(2, 2)

    assert backend.bridge_networks == [
        ("bjtu_10.10.0.0/24", "10.10.0.0/24"),
        ("bjtu_10.10.1.0/24", "10.10.1.0/24"),
        ("bjtu_10.10.2.0/24", "10.10.2.0/24"),
        ("bjtu_10.10.3.0/24", "10.10.3.0/24"),
    ]
    assert simulation.get_topo()["edges"] == [
        ("node_1", "node_2"),
        ("node_1", "node_3"),
        ("node_2", "node_4"),
        ("node_3", "node_4"),
    ]
    assert {node.name for node in simulation.nodes} == {"node_1", "node_2", "node_3", "node_4"}
