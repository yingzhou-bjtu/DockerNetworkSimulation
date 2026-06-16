import pika
import uuid
import json


class VireClient:
    def __init__(self):
        # 连接RabbitMQ服务器
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()

        # 声明交换器
        self.channel.exchange_declare(exchange='vire-bjtu-exchange', exchange_type='direct')
        self.channel.exchange_declare(exchange='bjtu-vire-exchange', exchange_type='direct')

        # 声明接收响应的队列
        result = self.channel.queue_declare(queue='bjtu-vire-queue')
        self.callback_queue = result.method.queue

        # 将交换器与队列绑定
        self.channel.queue_bind(exchange='bjtu-vire-exchange', queue='bjtu-vire-queue', routing_key='')
        self.channel.queue_bind(exchange='vire-bjtu-exchange', queue='vire-bjtu-queue', routing_key='')

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
        print(f"-> send to vire-bjtu-exchange: {message}")

        # 发送消息到"未尔->北交"的交换器和队列
        self.channel.basic_publish(
            exchange='vire-bjtu-exchange',  # 使用未尔->北交的交换器
            routing_key='',  # 路由键为空，使用默认绑定
            properties=pika.BasicProperties(
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
