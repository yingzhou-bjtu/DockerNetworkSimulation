import argparse
import subprocess


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Open interactive shells for simulator containers.")
    parser.add_argument("container_ids", nargs="+", help="Docker container IDs or names.")
    return parser.parse_args(argv)


def build_terminal_command(container_id):
    container_id = container_id.strip()
    if not container_id:
        raise ValueError("container_id must not be empty")
    return [
        "gnome-terminal",
        "--title",
        container_id,
        "--",
        "bash",
        "-c",
        'docker exec -it "$1" bash; exec bash',
        "docker-shell",
        container_id,
    ]


def main(argv=None):
    args = parse_args(argv)
    for container_id in args.container_ids:
        subprocess.run(build_terminal_command(container_id), check=True)


if __name__ == "__main__":
    main()
