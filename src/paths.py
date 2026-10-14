import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR_ENV = "ROUTING_SIM_OUTPUT_DIR"
CONFIG_DIR_ENV = "ROUTING_SIM_CONFIG_DIR"


def resolve_project_path(value=None, *, env_var=None, default_relative=None):
    configured_value = value
    if configured_value is None and env_var:
        configured_value = os.environ.get(env_var)
    if configured_value is None:
        if default_relative is None:
            raise ValueError("No path value or default was provided.")
        configured_value = default_relative

    path = Path(configured_value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def get_output_dir(output_dir=None, *, create=True):
    path = resolve_project_path(
        output_dir,
        env_var=OUTPUT_DIR_ENV,
        default_relative="output",
    )
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_dir(config_dir=None):
    path = resolve_project_path(
        config_dir,
        env_var=CONFIG_DIR_ENV,
        default_relative="configs",
    )
    if not path.is_dir():
        raise FileNotFoundError(f"Configuration directory does not exist: {path}")
    return path


def get_config_path(filename, config_dir=None):
    path = get_config_dir(config_dir) / filename
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file does not exist: {path}")
    return path
