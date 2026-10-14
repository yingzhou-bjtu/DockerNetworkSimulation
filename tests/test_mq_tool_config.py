from pathlib import Path

from mq_tool import VireClientConfig, load_vire_client_config


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
