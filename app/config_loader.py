import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .rabbitmq_config import StandardRabbitMQConfig, require_non_empty_string


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API_CONFIG = PROJECT_ROOT / 'configs' / 'api_config.toml'
DEFAULT_MQ_CONFIG = PROJECT_ROOT / 'configs' / 'mq_config.json'
API_CONFIG_ENV = 'ROUTING_SIM_API_CONFIG'
MQ_CONFIG_ENV = 'ROUTING_SIM_MQ_CONFIG'


def require_port(field_name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f'{field_name} must be an integer')
    if value < 1 or value > 65535:
        raise ValueError(f'{field_name} must be in 1..65535')
    return value


def require_mapping(field_name, value):
    if not isinstance(value, Mapping):
        raise TypeError(f'{field_name} must be a mapping/table')
    return value


@dataclass(frozen=True)
class FlaskConfig:
    host: str = '0.0.0.0'
    port: int = 5000
    debug: bool = False

    def __post_init__(self):
        require_non_empty_string('host', self.host)
        require_port('port', self.port)
        if not isinstance(self.debug, bool):
            raise TypeError('debug must be a boolean')

    @classmethod
    def from_mapping(cls, config):
        return cls(
            host=config.get('host', cls.host),
            port=config.get('port', cls.port),
            debug=config.get('debug', cls.debug),
        )

    def as_flask_kwargs(self):
        return {
            'host': self.host,
            'port': self.port,
            'debug': self.debug,
        }


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
        return self.get_typed_flask_config().as_flask_kwargs()

    def get_typed_flask_config(self):
        flask_config = require_mapping('flask', self.config.get('flask', {}))
        return FlaskConfig.from_mapping(flask_config)

    def get_rabbitmq_config(self):
        rabbitmq_config = require_mapping(
            'rabbitmq',
            self.config.get('rabbitmq', {}),
        )
        exchange_config = require_mapping(
            'rabbitmq.exchange',
            rabbitmq_config.get('exchange', {}),
        )
        queue_config = require_mapping(
            'rabbitmq.queues',
            rabbitmq_config.get('queues', {}),
        )
        routing_config = require_mapping(
            'rabbitmq.routing',
            rabbitmq_config.get('routing', {}),
        )
        return {
            "host": rabbitmq_config.get('host', 'localhost'),
            "exchange_name": exchange_config.get('name', 'default-exchange'),
            "exchange_type": exchange_config.get('type', 'direct'),
            "request_exchange": rabbitmq_config.get('request_exchange', 'vire-bjtu-exchange'),
            "inbound_queue": queue_config.get('inbound', 'queue1'),
            "outbound_queue": queue_config.get('outbound', 'queue2'),
            "routing_key": routing_config.get('key', '')
        }

    def get_standard_rabbitmq_config(self):
        return StandardRabbitMQConfig.from_mapping(self.get_rabbitmq_config())

    def get_api_type(self):
        app_config = require_mapping('app', self.config.get('app', {}))
        return app_config.get('api_type', ['flask'])
