import random

import pytest

from app.mq_api_handler import NetworkAPIHandler
from src.network_simulation import NetworkSimulation
from src.nodes import Node
from src.paths import get_config_dir, get_output_dir
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


def test_topology_planners_reject_invalid_dimensions():
    with pytest.raises(ValueError, match="count"):
        random_router_topology(0)

    with pytest.raises(TypeError, match="count"):
        random_router_topology(True)

    with pytest.raises(ValueError, match="at least 3"):
        circle_router_topology(2)

    with pytest.raises(ValueError, match="rows"):
        grid_router_topology(0, 2)

    with pytest.raises(TypeError, match="cols"):
        grid_router_topology(2, "3")


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


def test_network_simulation_uses_configured_output_directory(tmp_path):
    output_dir = tmp_path / "generated"
    simulation = NetworkSimulation(docker_backend=MemoryNetworkBackend(), output_dir=output_dir)

    simulation.create_grid_nodes(1, 2)

    assert simulation.output_dir == output_dir.resolve()
    assert {node.output_dir for node in simulation.nodes} == {output_dir.resolve()}


def test_cleanup_config_files_uses_configured_output_directory(tmp_path):
    simulation = NetworkSimulation(docker_backend=MemoryNetworkBackend(), output_dir=tmp_path)
    conf_file = tmp_path / "node.conf"
    log_file = tmp_path / "node.log"
    keep_file = tmp_path / "keep.json"
    conf_file.write_text("conf", encoding="utf-8")
    log_file.write_text("log", encoding="utf-8")
    keep_file.write_text("{}", encoding="utf-8")

    simulation.cleanup_config_files()

    assert not conf_file.exists()
    assert not log_file.exists()
    assert keep_file.exists()


def test_network_api_handler_writes_mapping_to_configured_output_dir(tmp_path):
    handler = NetworkAPIHandler(output_dir=tmp_path)

    handler.create_mapping([{"ExternalIP": "192.0.2.10", "SimIP": "10.0.0.2"}])

    assert (tmp_path / "forward_targets.json").read_text(encoding="utf-8") == (
        '{"forward_targets": [{"source": "192.0.2.10", "destination": "10.0.0.2"}]}'
    )


def test_path_helpers_accept_environment_overrides(tmp_path, monkeypatch):
    output_dir = tmp_path / "out"
    config_dir = tmp_path / "cfg"
    config_dir.mkdir()
    monkeypatch.setenv("ROUTING_SIM_OUTPUT_DIR", str(output_dir))
    monkeypatch.setenv("ROUTING_SIM_CONFIG_DIR", str(config_dir))

    assert get_output_dir() == output_dir.resolve()
    assert get_config_dir() == config_dir.resolve()


def test_apply_tc_delay_rejects_invalid_parameters_before_container_access():
    node = Node("node_1", ip_allocator=None, group_label="test", networks={})

    invalid_parameters = [
        {"delay": 100},
        {"jitter": 10},
        {"loss": -1.0},
        {"loss": 101.0},
        {"loss": 1},
        {"max_queue_size": 0},
        {"max_queue_size": 1.5},
    ]

    for parameters in invalid_parameters:
        with pytest.raises(ValueError):
            node.apply_tc_delay("eth0", **parameters)


def test_apply_tc_on_edges_rejects_unknown_topology_edges():
    simulation = NetworkSimulation(docker_backend=MemoryNetworkBackend())
    simulation.create_grid_nodes(1, 2)

    with pytest.raises(ValueError, match="不在图中"):
        simulation.apply_tc_on_edges([("node_2", "node_3")])


def test_apply_tc_on_edges_rejects_missing_nodes():
    simulation = NetworkSimulation(docker_backend=MemoryNetworkBackend())
    simulation.create_grid_nodes(1, 2)
    simulation.nodes.clear()

    with pytest.raises(ValueError, match="不存在"):
        simulation.apply_tc_on_edges([("node_1", "node_2")])
