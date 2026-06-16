# import threading
# from app.config_loader import ConfigLoader
# from app.network_api_handler import NetworkAPIHandler
# from app.app_mq import start_rabbitmq_consumer
# from app.app_restful import start_flask_app
from app.app_mq_joint import start_rabbitmq_consumer


def main():
    # config_loader = ConfigLoader()  # 载入配置文件
    # flask_config = config_loader.get_flask_config()
    # rabbitmq_config = config_loader.get_rabbitmq_config()
    # api_type = config_loader.get_api_type()
    # network_handler = NetworkAPIHandler()

    # threads = []
    # if 'flask' in api_type:
    #     threads.append(threading.Thread(target=start_flask_app, args=(network_handler, flask_config)))
    # if 'rabbitmq' in api_type:
    #     threads.append(threading.Thread(target=start_rabbitmq_consumer, args=(network_handler, rabbitmq_config)))

    # 启动线程
    # for thread in threads:
    #     thread.start()
    # for thread in threads:  # 阻塞，避免ThreadPoolExecutor引发错误
    #     thread.join()

    start_rabbitmq_consumer()


if __name__ == "__main__":
    main()
