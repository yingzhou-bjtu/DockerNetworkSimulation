import os
import toml


class ConfigLoader:
    def __init__(self, config_file='../configs/api_config.toml'):
        self.config = toml.load(os.path.join(os.path.abspath(os.path.dirname(__file__)), config_file))

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
            "inbound_queue": rabbitmq_config.get('queues', {}).get('inbound', 'queue1'),
            "outbound_queue": rabbitmq_config.get('queues', {}).get('outbound', 'queue2'),
            "routing_key": rabbitmq_config.get('routing', {}).get('key', '')
        }

    def get_api_type(self):
        return self.config.get('app', {}).get('api_type', ['flask'])
