import argparse
import subprocess


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Open interactive shells for simulator containers.")
    parser.add_argument("container_ids", nargs="+", help="Docker container IDs or names.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    for container_id in args.container_ids:
        subprocess.run(
            [
                "gnome-terminal",
                "--title",
                container_id,
                "--",
                "bash",
                "-c",
                f"docker exec -it {container_id} bash; exec bash",
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
