import argparse

from app.service_runner import start_configured_services, start_joint_mq_service


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Start the routing simulator API service.')
    parser.add_argument(
        '--mode',
        choices=('joint-mq', 'configured'),
        default='joint-mq',
        help='Service mode. joint-mq keeps the current MQ integration path; configured uses api_config.toml.',
    )
    parser.add_argument(
        '--config',
        help='Config path for the selected mode: mq_config.json for joint-mq, api_config.toml for configured.',
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.mode == 'configured':
        start_configured_services(args.config)
    else:
        start_joint_mq_service(args.config)


if __name__ == "__main__":
    main()
