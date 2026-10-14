import json
from typing import TYPE_CHECKING

from .rabbitmq_config import ensure_standard_rabbitmq_config

if TYPE_CHECKING:
    from .network_api_handler import NetworkAPIHandler


class RabbitMQHandler:
    def __init__(self, network_handler, config):
        import pika

        self._pika = pika
        self.network_handler: 'NetworkAPIHandler' = network_handler
        self.config = ensure_standard_rabbitmq_config(config)

        self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.config.host))
        self.channel = self.connection.channel()

        # 声明交换器和队列
        self.channel.exchange_declare(exchange=self.config.exchange_name, exchange_type=self.config.exchange_type)
        self.channel.queue_declare(queue=self.config.inbound_queue)
        self.channel.queue_declare(queue=self.config.outbound_queue)

        self.channel.queue_bind(exchange=self.config.exchange_name,
                                queue=self.config.outbound_queue,
                                routing_key=self.config.routing_key)

    def process_message(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            link = message.get('link', '')

            if link == '/cleanup':
                response = self.network_handler.cleanup()
            elif link == '/start':
                response = self.network_handler.start_simulation(message, use_thread=False)
            elif link == '/stop':
                response = self.network_handler.stop_simulation()
            elif link == '/status':
                response = self.network_handler.get_status()
            elif link == '/node/ipaddr':
                node_name = message.get('node_name')
                response = self.network_handler.get_node_ipaddr(node_name)
            elif link == '/node/iproute':
                node_name = message.get('node_name')
                response = self.network_handler.get_node_iproute(node_name)
            elif link == '/get-delay':
                src_node_name = message.get('src_node_name')
                dst_node_name = message.get('dst_node_name')
                response = self.network_handler.get_pair_delay(src_node_name, dst_node_name)
            elif link == '/set_delay':
                response = self.network_handler.set_tc_on_edges(message)
            else:
                response = {"state": 0, "msg": "未识别的 link"}

            self.publish_response(ch, properties.correlation_id, response)

        except Exception as e:
            error_response = {"state": 1, "msg": f"错误详情：{e}"}
            self.publish_response(ch, properties.correlation_id, error_response)

        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def publish_response(self, ch, correlation_id, response):
        ch.basic_publish(
            exchange=self.config.exchange_name,
            routing_key=self.config.routing_key,
            properties=self._pika.BasicProperties(
                correlation_id=correlation_id
            ),
            body=json.dumps(response)
        )

    def start_consuming(self):
        self.channel.basic_consume(queue=self.config.inbound_queue, on_message_callback=self.process_message)
        print(f'-> RabbitMQ API已启动，正在监听 {self.config.inbound_queue}')
        self.channel.start_consuming()


def start_rabbitmq_consumer(network_handler, config):
    rabbitmq_handler = RabbitMQHandler(network_handler, config)
    rabbitmq_handler.start_consuming()
