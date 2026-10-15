from pathlib import Path

import pytest

from app.config_loader import ConfigLoader, FlaskConfig, load_json_config
from app.rabbitmq_config import (
    JointRabbitMQConfig,
    JointRabbitMQQueues,
    StandardRabbitMQConfig,
    ensure_joint_rabbitmq_config,
    ensure_standard_rabbitmq_config,
)
from mq_tool import VireClientConfig, load_vire_client_config
from app.simulation_request import parse_simulation_request


def test_simulation_request_normalizes_static_topology():
    request = parse_simulation_request(
        {
            "topology_type": "static",
            "static_topology": {
                "nodes": [
                    {
                        "name": "node_1",
                        "type": "router",
                        "coordinates": {"latitude": 1.0, "longitude": 2.0},
                    }
                ],
                "edges": [],
            },
            "use_static_routes": True,
        }
    )

    assert request.topology_type == "static"
    assert request.static_topology["nodes"][0]["name"] == "node_1"
    assert request.static_topology["edges"] == []
    assert request.use_static_routes is True


def test_simulation_request_normalizes_random_topology():
    request = parse_simulation_request({"topology_type": "random", "node_count": 4})

    assert request.topology_type == "random"
    assert request.node_count == 4
    assert request.lisp_mode == "none"


def test_simulation_request_rejects_zero_node_count():
    with pytest.raises(ValueError, match="node_count"):
        parse_simulation_request({"topology_type": "random", "node_count": 0})


def test_simulation_request_rejects_boolean_node_count():
    with pytest.raises(ValueError, match="node_count"):
        parse_simulation_request({"topology_type": "random", "node_count": True})


def test_simulation_request_rejects_invalid_lisp_counts():
    with pytest.raises(ValueError, match="ms_count"):
        parse_simulation_request(
            {
                "topology_type": "random",
                "node_count": 4,
                "lisp_mode": "simulation",
                "xtr_count": 2,
                "ms_count": 0,
            }
        )


def test_simulation_request_validates_static_topology_graph():
    valid_node = {
        "name": "node_1",
        "coordinates": {"latitude": 1.0, "longitude": 2.0},
    }
    cases = (
        ({"nodes": [], "edges": []}, "non-empty list"),
        ({"nodes": ["bad"], "edges": []}, "must be an object"),
        ({"nodes": [{"name": "", "coordinates": {}}], "edges": []}, "non-empty string"),
        ({"nodes": [{**valid_node, "coordinates": None}], "edges": []}, "coordinates"),
        ({"nodes": [valid_node, valid_node], "edges": []}, "duplicate"),
        ({"nodes": [valid_node], "edges": [["node_1"]]}, "two node names"),
        ({"nodes": [valid_node], "edges": [["node_1", "node_1"]]}, "self-loop"),
        ({"nodes": [valid_node], "edges": [["node_1", "missing"]]}, "unknown nodes"),
    )
    for topology, message in cases:
        with pytest.raises(ValueError, match=message):
            parse_simulation_request(
                {"topology_type": "static", "static_topology": topology}
            )


def test_config_loader_exposes_typed_standard_rabbitmq_config():
    config = ConfigLoader(Path("configs/api_config.toml")).get_standard_rabbitmq_config()

    assert config == StandardRabbitMQConfig(
        host="localhost",
        exchange_name="bjtu-vire-exchange",
        exchange_type="direct",
        request_exchange="vire-bjtu-exchange",
        inbound_queue="vire-bjtu-queue",
        outbound_queue="bjtu-vire-queue",
        routing_key="",
    )


def test_config_loader_validates_flask_config():
    config_loader = ConfigLoader(Path("configs/api_config.toml"))

    assert config_loader.get_typed_flask_config() == FlaskConfig(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )
    assert config_loader.get_flask_config() == {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": False,
    }


def test_config_loader_rejects_invalid_flask_config(tmp_path):
    bad_port_config = tmp_path / "bad_port.toml"
    bad_port_config.write_text(
        "\n".join(
            [
                "[flask]",
                'host = "0.0.0.0"',
                "port = 70000",
                "debug = false",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="port"):
        ConfigLoader(bad_port_config).get_typed_flask_config()

    bad_debug_config = tmp_path / "bad_debug.toml"
    bad_debug_config.write_text(
        "\n".join(
            [
                "[flask]",
                'host = "0.0.0.0"',
                "port = 5000",
                'debug = "yes"',
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(TypeError, match="debug"):
        ConfigLoader(bad_debug_config).get_typed_flask_config()


def test_config_loader_rejects_non_mapping_sections(tmp_path):
    cases = {
        "flask": '\n'.join(['flask = "bad"']),
        "rabbitmq": '\n'.join(['rabbitmq = "bad"']),
        "rabbitmq.exchange": '\n'.join(['[rabbitmq]', 'exchange = "bad"']),
        "rabbitmq.queues": '\n'.join(['[rabbitmq]', 'queues = ["bad"]']),
        "rabbitmq.routing": '\n'.join(['[rabbitmq]', 'routing = 1']),
        "app": '\n'.join(['app = ["bad"]']),
    }
    for name, text in cases.items():
        config_path = tmp_path / f"{name.replace('.', '_')}.toml"
        config_path.write_text(text, encoding="utf-8")
        loader = ConfigLoader(config_path)

        with pytest.raises(TypeError, match=name):
            if name == "flask":
                loader.get_typed_flask_config()
            elif name == "rabbitmq":
                loader.get_rabbitmq_config()
            elif name.startswith("rabbitmq."):
                loader.get_rabbitmq_config()
            else:
                loader.get_api_type()


def test_load_vire_client_config_uses_toml_rabbitmq_section():
    config = load_vire_client_config(Path("configs/api_config.toml"))

    assert config == VireClientConfig(
        host="localhost",
        exchange_type="direct",
        request_exchange="vire-bjtu-exchange",
        response_exchange="bjtu-vire-exchange",
        request_queue="vire-bjtu-queue",
        response_queue="bjtu-vire-queue",
        routing_key="",
    )


def test_joint_rabbitmq_config_uses_json_queue_schema():
    config = JointRabbitMQConfig.from_mapping(load_json_config(Path("configs/mq_config.json")))

    assert config.host == "192.168.124.107"
    assert config.exchange == "gr_fe_exchange"
    assert config.exchange_type == "fanout"
    assert config.queues.names() == (
        "control_queue_gr",
        "fe_gr_queue_nodeinfo",
        "fe_gr_queue_topo",
        "fe_gr_queue_map",
    )


def test_rabbitmq_config_compatibility_converters_accept_existing_instances():
    standard_config = ConfigLoader(Path("configs/api_config.toml")).get_standard_rabbitmq_config()
    joint_config = JointRabbitMQConfig.from_mapping(load_json_config(Path("configs/mq_config.json")))

    assert ensure_standard_rabbitmq_config(standard_config) is standard_config
    assert ensure_joint_rabbitmq_config(joint_config) is joint_config


def test_rabbitmq_config_rejects_empty_connection_fields():
    with pytest.raises(ValueError, match="host"):
        StandardRabbitMQConfig(host=" ")

    with pytest.raises(ValueError, match="topo_queue"):
        JointRabbitMQQueues(
            control_queue_gr="control",
            nodeinfo_queue="nodeinfo",
            topo_queue="",
            map_queue="map",
        )


def test_joint_rabbitmq_config_rejects_untyped_queue_mapping():
    with pytest.raises(TypeError, match="JointRabbitMQQueues"):
        JointRabbitMQConfig(
            host="localhost",
            username="guest",
            password="guest",
            exchange="exchange",
            exchange_type="direct",
            queues={"control_queue_gr": "control"},
        )
