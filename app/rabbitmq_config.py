from dataclasses import dataclass


@dataclass(frozen=True)
class StandardRabbitMQConfig:
    host: str = 'localhost'
    exchange_name: str = 'default-exchange'
    exchange_type: str = 'direct'
    request_exchange: str = 'vire-bjtu-exchange'
    inbound_queue: str = 'queue1'
    outbound_queue: str = 'queue2'
    routing_key: str = ''

    @classmethod
    def from_mapping(cls, config):
        return cls(
            host=config.get('host', cls.host),
            exchange_name=config.get('exchange_name', cls.exchange_name),
            exchange_type=config.get('exchange_type', cls.exchange_type),
            request_exchange=config.get('request_exchange', cls.request_exchange),
            inbound_queue=config.get('inbound_queue', cls.inbound_queue),
            outbound_queue=config.get('outbound_queue', cls.outbound_queue),
            routing_key=config.get('routing_key', cls.routing_key),
        )


@dataclass(frozen=True)
class VireClientConfig:
    host: str = 'localhost'
    exchange_type: str = 'direct'
    request_exchange: str = 'vire-bjtu-exchange'
    response_exchange: str = 'bjtu-vire-exchange'
    request_queue: str = 'vire-bjtu-queue'
    response_queue: str = 'bjtu-vire-queue'
    routing_key: str = ''

    @classmethod
    def from_standard_config(cls, config):
        standard_config = ensure_standard_rabbitmq_config(config)
        return cls(
            host=standard_config.host,
            exchange_type=standard_config.exchange_type,
            request_exchange=standard_config.request_exchange,
            response_exchange=standard_config.exchange_name,
            request_queue=standard_config.inbound_queue,
            response_queue=standard_config.outbound_queue,
            routing_key=standard_config.routing_key,
        )


@dataclass(frozen=True)
class JointRabbitMQQueues:
    control_queue_gr: str
    nodeinfo_queue: str
    topo_queue: str
    map_queue: str

    @classmethod
    def from_mapping(cls, queues):
        return cls(
            control_queue_gr=queues['control_queue_gr'],
            nodeinfo_queue=queues['nodeinfo_queue'],
            topo_queue=queues['topo_queue'],
            map_queue=queues['map_queue'],
        )

    def names(self):
        return (
            self.control_queue_gr,
            self.nodeinfo_queue,
            self.topo_queue,
            self.map_queue,
        )


@dataclass(frozen=True)
class JointRabbitMQConfig:
    host: str
    username: str
    password: str
    exchange: str
    exchange_type: str
    queues: JointRabbitMQQueues

    @classmethod
    def from_mapping(cls, config):
        return cls(
            host=config['host'],
            username=config['username'],
            password=config['password'],
            exchange=config['exchange'],
            exchange_type=config['exchange_type'],
            queues=JointRabbitMQQueues.from_mapping(config['queues']),
        )


def ensure_standard_rabbitmq_config(config):
    if isinstance(config, StandardRabbitMQConfig):
        return config
    return StandardRabbitMQConfig.from_mapping(config)


def ensure_joint_rabbitmq_config(config):
    if isinstance(config, JointRabbitMQConfig):
        return config
    return JointRabbitMQConfig.from_mapping(config)
