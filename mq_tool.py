from dataclasses import dataclass
import uuid
import json

from app.config_loader import ConfigLoader


@dataclass(frozen=True)
class VireClientConfig:
    host: str = 'localhost'
    exchange_type: str = 'direct'
    request_exchange: str = 'vire-bjtu-exchange'
    response_exchange: str = 'bjtu-vire-exchange'
    request_queue: str = 'vire-bjtu-queue'
    response_queue: str = 'bjtu-vire-queue'
    routing_key: str = ''


def load_vire_client_config(config_file=None):
    rabbitmq_config = ConfigLoader(config_file).get_rabbitmq_config()
    return VireClientConfig(
        host=rabbitmq_config['host'],
        exchange_type=rabbitmq_config['exchange_type'],
        request_exchange=rabbitmq_config.get('request_exchange', VireClientConfig.request_exchange),
        response_exchange=rabbitmq_config['exchange_name'],
        request_queue=rabbitmq_config['inbound_queue'],
        response_queue=rabbitmq_config['outbound_queue'],
        routing_key=rabbitmq_config['routing_key'],
    )


class VireClient:
    def __init__(self, config=None, config_file=None):
        import pika

        self._pika = pika
        self.config = config or load_vire_client_config(config_file)
        # 连接RabbitMQ服务器
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.config.host))
        self.channel = self.connection.channel()

        # 声明交换器
        self.channel.exchange_declare(exchange=self.config.request_exchange, exchange_type=self.config.exchange_type)
        self.channel.exchange_declare(exchange=self.config.response_exchange, exchange_type=self.config.exchange_type)

        # 声明接收响应的队列
        result = self.channel.queue_declare(queue=self.config.response_queue)
        self.callback_queue = result.method.queue

        # 将交换器与队列绑定
        self.channel.queue_bind(
            exchange=self.config.response_exchange,
            queue=self.config.response_queue,
            routing_key=self.config.routing_key,
        )
        self.channel.queue_bind(
            exchange=self.config.request_exchange,
            queue=self.config.request_queue,
            routing_key=self.config.routing_key,
        )

        # 监听回调队列中的消息
        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True
        )

        self.response = None
        self.corr_id = None

    # 处理接收的响应
    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = json.loads(body)
            print(f"-> received: {self.response}")

    # 发送消息并等待响应
    def call(self, message):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        print(f"-> send to {self.config.request_exchange}: {message}")

        # 发送消息到"未尔->北交"的交换器和队列
        self.channel.basic_publish(
            exchange=self.config.request_exchange,  # 使用未尔->北交的交换器
            routing_key=self.config.routing_key,
            properties=self._pika.BasicProperties(
                reply_to=self.callback_queue,  # 指定接收响应的队列
                correlation_id=self.corr_id  # 唯一的correlation_id用于匹配响应
            ),
            body=json.dumps(message)
        )

        # 等待响应
        while self.response is None:
            self.connection.process_data_events()

        return self.response


# 模拟发送消息并接收响应
def simulate_vire():
    client = VireClient()

    # 清理环境
    # message = {"link": "/cleanup"}

    # 启动模拟环境
    message = {
        "link": "/start",
        "topology_type": "static",
        "static_topology": {
            "edges": [
                [
                    "node_1",
                    "node_2"
                ],
                [
                    "node_2",
                    "node_3"
                ],
                [
                    "node_3",
                    "node_4"
                ]
            ],
            "nodes": [
                "node_1",
                "node_2",
                "node_3",
                "node_4"
            ]
        },
        "node_count": 5,
        "lisp_mode": "simulation",
        "xtr_count": 2,
        "ms_count": 1,
        "use_static_routes": True
    }

    # message = {"link": "/get-delay", "src_node_name": "xTR1", "dst_node_name": "xTR2"}

    # 清理
    # message = {"link": "/cleanup"}

    # 获取状态
    # message = {"link": "/status"}

    # 停止模拟环境
    # message = {"link": "/stop"}

    client.call(message)


if __name__ == "__main__":
    simulate_vire()
