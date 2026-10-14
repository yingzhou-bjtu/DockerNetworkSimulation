from pathlib import Path

import pytest

from app.config_loader import ConfigLoader, load_json_config
from app.rabbitmq_config import (
    JointRabbitMQConfig,
    JointRabbitMQQueues,
    StandardRabbitMQConfig,
    ensure_joint_rabbitmq_config,
    ensure_standard_rabbitmq_config,
)
from mq_tool import VireClientConfig, load_vire_client_config


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
