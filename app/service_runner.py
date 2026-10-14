import threading


VALID_API_TYPES = {'flask', 'rabbitmq'}


def normalize_api_types(raw_api_types):
    if isinstance(raw_api_types, str):
        api_types = [raw_api_types]
    else:
        api_types = list(raw_api_types or [])

    normalized = []
    for api_type in api_types:
        value = str(api_type).strip().lower()
        if not value:
            continue
        if value not in VALID_API_TYPES:
            raise ValueError(f'Unsupported API type: {api_type}')
        if value not in normalized:
            normalized.append(value)

    if not normalized:
        raise ValueError('At least one API type must be configured.')
    return normalized


def start_joint_mq_service(config_file=None):
    from .app_mq_joint import start_rabbitmq_consumer

    start_rabbitmq_consumer(config_file)


def start_configured_services(config_file=None):
    from .app_mq import start_rabbitmq_consumer as start_standard_rabbitmq
    from .app_restful import start_flask_app
    from .config_loader import ConfigLoader
    from .network_api_handler import NetworkAPIHandler

    config_loader = ConfigLoader(config_file)
    api_types = normalize_api_types(config_loader.get_api_type())
    network_handler = NetworkAPIHandler()
    threads = []

    if 'flask' in api_types:
        threads.append(
            threading.Thread(
                target=start_flask_app,
                args=(network_handler, config_loader.get_flask_config()),
                name='routing-sim-flask',
            )
        )
    if 'rabbitmq' in api_types:
        threads.append(
            threading.Thread(
                target=start_standard_rabbitmq,
                args=(network_handler, config_loader.get_standard_rabbitmq_config()),
                name='routing-sim-rabbitmq',
            )
        )

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
