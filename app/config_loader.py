import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API_CONFIG = PROJECT_ROOT / 'configs' / 'api_config.toml'
DEFAULT_MQ_CONFIG = PROJECT_ROOT / 'configs' / 'mq_config.json'
API_CONFIG_ENV = 'ROUTING_SIM_API_CONFIG'
MQ_CONFIG_ENV = 'ROUTING_SIM_MQ_CONFIG'


def resolve_config_path(config_file=None, *, env_var=None, default_path=None):
    """Resolve config paths from an explicit value, environment, or project default."""
    configured_path = config_file or (os.environ.get(env_var) if env_var else None) or default_path
    if configured_path is None:
        raise ValueError('No configuration path was provided.')

    path = Path(configured_path).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path = path.resolve()

    if not path.is_file():
        source = f'${env_var}' if env_var and os.environ.get(env_var) else 'argument/default'
        raise FileNotFoundError(f'Configuration file from {source} does not exist: {path}')
    return path


def load_json_config(config_file=None, *, env_var=MQ_CONFIG_ENV, default_path=DEFAULT_MQ_CONFIG):
    config_path = resolve_config_path(config_file, env_var=env_var, default_path=default_path)
    with config_path.open('r', encoding='utf-8') as config_file_obj:
        return json.load(config_file_obj)


class ConfigLoader:
    def __init__(self, config_file=None):
        import toml

        self.config_path = resolve_config_path(
            config_file,
            env_var=API_CONFIG_ENV,
            default_path=DEFAULT_API_CONFIG,
        )
        self.config = toml.load(self.config_path)

    def get_flask_config(self):
        flask_config = self.config.get('flask', {})
        return {
            "host": flask_config.get('host', '0.0.0.0'),
            "port": flask_config.get('port', 5000),
            "debug": flask_config.get('debug', False)
        }

    def get_rabbitmq_config(self):
        rabbitmq_config = self.config.get('rabbitmq', {})
        return {
            "host": rabbitmq_config.get('host', 'localhost'),
            "exchange_name": rabbitmq_config.get('exchange', {}).get('name', 'default-exchange'),
            "exchange_type": rabbitmq_config.get('exchange', {}).get('type', 'direct'),
            "request_exchange": rabbitmq_config.get('request_exchange', 'vire-bjtu-exchange'),
            "inbound_queue": rabbitmq_config.get('queues', {}).get('inbound', 'queue1'),
            "outbound_queue": rabbitmq_config.get('queues', {}).get('outbound', 'queue2'),
            "routing_key": rabbitmq_config.get('routing', {}).get('key', '')
        }

    def get_api_type(self):
        return self.config.get('app', {}).get('api_type', ['flask'])
