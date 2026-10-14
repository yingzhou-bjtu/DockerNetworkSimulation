from dataclasses import dataclass


def require_non_empty_string(field_name, value):
    if not isinstance(value, str):
        raise TypeError(f'{field_name} must be a string')
    if not value.strip():
        raise ValueError(f'{field_name} must not be empty')
    return value


def require_string(field_name, value):
    if not isinstance(value, str):
        raise TypeError(f'{field_name} must be a string')
    return value


@dataclass(frozen=True)
class StandardRabbitMQConfig:
    host: str = 'localhost'
    exchange_name: str = 'default-exchange'
    exchange_type: str = 'direct'
    request_exchange: str = 'vire-bjtu-exchange'
    inbound_queue: str = 'queue1'
    outbound_queue: str = 'queue2'
    routing_key: str = ''

    def __post_init__(self):
        require_non_empty_string('host', self.host)
        require_non_empty_string('exchange_name', self.exchange_name)
        require_non_empty_string('exchange_type', self.exchange_type)
        require_non_empty_string('request_exchange', self.request_exchange)
        require_non_empty_string('inbound_queue', self.inbound_queue)
        require_non_empty_string('outbound_queue', self.outbound_queue)
        require_string('routing_key', self.routing_key)

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

    def __post_init__(self):
        require_non_empty_string('host', self.host)
        require_non_empty_string('exchange_type', self.exchange_type)
        require_non_empty_string('request_exchange', self.request_exchange)
        require_non_empty_string('response_exchange', self.response_exchange)
        require_non_empty_string('request_queue', self.request_queue)
        require_non_empty_string('response_queue', self.response_queue)
        require_string('routing_key', self.routing_key)

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

    def __post_init__(self):
        require_non_empty_string('control_queue_gr', self.control_queue_gr)
        require_non_empty_string('nodeinfo_queue', self.nodeinfo_queue)
        require_non_empty_string('topo_queue', self.topo_queue)
        require_non_empty_string('map_queue', self.map_queue)

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

    def __post_init__(self):
        require_non_empty_string('host', self.host)
        require_non_empty_string('username', self.username)
        require_non_empty_string('password', self.password)
        require_non_empty_string('exchange', self.exchange)
        require_non_empty_string('exchange_type', self.exchange_type)
        if not isinstance(self.queues, JointRabbitMQQueues):
            raise TypeError('queues must be a JointRabbitMQQueues instance')

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
