import argparse
import json
from .config_loader import MQ_CONFIG_ENV, load_json_config
from .rabbitmq_config import JointRabbitMQConfig, ensure_joint_rabbitmq_config


class RabbitMQHandler:
    def __init__(self, config):
        """
        初始化RabbitMQ连接
        :param config: RabbitMQ service configuration.
        """
        from .mq_api_handler import NetworkAPIHandler

        self.config = ensure_joint_rabbitmq_config(config)
        self.handler = NetworkAPIHandler(self.send_message)

        # 从配置字典中读取参数
        self.host = self.config.host
        self.exchange = self.config.exchange
        self.exchange_type = self.config.exchange_type
        self.queues = self.config.queues
        self.username = self.config.username
        self.password = self.config.password

        self.connection, self.channel = self.create_connection_and_channel()
        self.connection_send, self.channel_send = self.create_connection_and_channel()

        # 声明交换器
        self.channel.exchange_declare(exchange=self.exchange, exchange_type=self.exchange_type,
                                      auto_delete=False, durable=True)

        # 声明队列
        for queue in self.queues.names():
            self.channel.queue_declare(queue=queue, auto_delete=False, durable=True)

    def create_connection_and_channel(self):
        import pika

        credentials = pika.PlainCredentials(self.username, self.password)
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host,
                                                                       credentials=credentials, heartbeat=0))
        channel = connection.channel()
        return connection, channel

    def process_control_queue(self, ch, method, properties, body):
        queue_name = self.queues.control_queue_gr
        # try:
        message = json.loads(body)
        print(f"-> 收到来自{queue_name}的消息: {message}")
        control = message.get('sim_control')
        if control:
            if control == 'sim_start':
                self.handler.start_simulation()

            elif control == 'sim_stop':
                self.handler.stop_simulation()

            elif control == 'sim_resume':
                self.handler.reset_info()
            else:
                print(f'未匹配的控制指令: {control}')
            return

        deactivate = message.get('DeactivateNode')
        if deactivate:
            print(f"Deactivating node: {deactivate}")
            return

        activate = message.get('ActivateNode')
        if activate:
            print(f"Activating node: {activate}")
            return

        print("未匹配的消息内容:", message)
        # except Exception as e:
        #     print(f"在{queue_name}中发生错误，详情：{e}")

    def process_nodeinfo_queue(self, ch, method, properties, body):
        queue_name = self.queues.nodeinfo_queue
        try:
            message = json.loads(body)
            print(f"-> 收到来自{queue_name}的消息: {message}")
            self.handler.config_nodes(message)
        except Exception as e:
            print(f"在{queue_name}中发生错误，详情：{e}")

    def process_topo_queue(self, ch, method, properties, body):
        queue_name = self.queues.topo_queue
        try:
            message = json.loads(body)
            print(f"-> 收到来自{queue_name}的消息: {message}")
            self.handler.config_topo(message)
        except Exception as e:
            print(f"在{queue_name}中发生错误，详情：{e}")

    def process_map_queue(self, ch, method, properties, body):
        queue_name = self.queues.map_queue
        try:
            message = json.loads(body)
            print(f"-> 收到来自{queue_name}的消息: {message}")
            create_mapping = message.get('CreateMapping')
            if create_mapping:
                self.handler.create_mapping(create_mapping)
                return
            remove_mapping = message.get('RemoveMapping')
            if remove_mapping:
                self.handler.remove_mapping()
                return

            print("未匹配的消息内容:", message)
        except Exception as e:
            print(f"在{queue_name}中发生错误，详情：{e}")

    def start_listening(self):
        self.channel.basic_consume(queue=self.queues.control_queue_gr,
                                   on_message_callback=self.process_control_queue, auto_ack=True)
        self.channel.basic_consume(queue=self.queues.nodeinfo_queue,
                                   on_message_callback=self.process_nodeinfo_queue, auto_ack=True)
        self.channel.basic_consume(queue=self.queues.topo_queue,
                                   on_message_callback=self.process_topo_queue, auto_ack=True)
        self.channel.basic_consume(queue=self.queues.map_queue,
                                   on_message_callback=self.process_map_queue, auto_ack=True)

        print(f'-> RabbitMQ API已启动，正在监听 {list(self.queues.names())}')
        self.channel.start_consuming()

    def send_message(self, message, routing_key=''):
        try:
            self.channel_send.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=json.dumps(message)
            )
            print(f"向{self.exchange}发送消息: {message}")
        except Exception as e:
            print(f"发送失败，详情: {e}")

    def close_connection(self):
        if self.connection:
            self.connection.close()
            self.connection_send.close()


def start_rabbitmq_consumer(config_file=None):
    config = JointRabbitMQConfig.from_mapping(load_json_config(config_file))
    rabbitmq_handler = RabbitMQHandler(config)
    # rabbitmq_handler.send_message({"test":"test"})
    try:
        rabbitmq_handler.start_listening()
    except KeyboardInterrupt:
        print("监听已停止")
    finally:
        rabbitmq_handler.close_connection()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Start the joint RabbitMQ API service.')
    parser.add_argument(
        '--config',
        help=f'Path to mq_config.json. Defaults to configs/mq_config.json or ${MQ_CONFIG_ENV}.',
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    start_rabbitmq_consumer(args.config)


if __name__ == '__main__':
    main()
