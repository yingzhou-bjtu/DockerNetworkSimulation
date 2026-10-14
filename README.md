# Containerized Routing Network Simulator

Containerized Routing Network Simulator is a Python-controlled toolkit for
Docker-based OSPF/LISP experiments. It can generate random routing topologies,
start Docker-based nodes, expose REST and RabbitMQ control paths, and write
topology/configuration artifacts for inspection.

## Project Identity

See [docs/PROJECT_IDENTITY.md](docs/PROJECT_IDENTITY.md) for the public name, repository slug, scope, and directory contract.

## Features

- Docker-based network and node orchestration.
- OSPF and LISP-oriented container build files.
- Flask REST API and RabbitMQ API handlers.
- NetworkX-based topology generation and visualization.
- Cleanup helpers for experiment containers and generated output.

## Repository Layout

```text
.
├── run.py                       # service entry point
├── quick_test.py                # lightweight simulation smoke check
├── quick_clean.py               # cleanup helper
├── src/                         # topology and simulation primitives
├── app/                         # REST and RabbitMQ API implementations
├── configs/                     # API, MQ, macvlan, and static topology config
├── docker/                      # Dockerfiles and protocol-specific build assets
├── oor-compose/                 # OpenOverlayRouter compose assets
├── images/                      # README and documentation images
├── output/                      # generated topology/config artifacts
└── docs/OPEN_SOURCE_STANDARD.md # repository hygiene and layout policy
```

## Requirements

- Python 3.10+
- Docker Engine with permission to build and run containers
- RabbitMQ when using the MQ API path

Install Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Build container images:

```bash
make -C docker
```

## Quick Start

Start the API service:

```bash
python run.py
```

Use a non-default MQ configuration:

```bash
python run.py --config configs/mq_config.json
```

Run a local smoke check:

```bash
python quick_test.py
```

Clean generated containers and networks:

```bash
python quick_clean.py
```

Generated topology and LISP files are written under `output/`.

## Configuration

- `configs/api_config.toml`: REST API configuration.
- `configs/mq_config.json`: RabbitMQ host, queue, and exchange settings.
- `configs/macvlan_configs.json`: macvlan-related host networking settings.
- `configs/static_topo*.json`: static topology examples.

Runtime configuration can be supplied with explicit paths or environment
variables:

```bash
python run.py --config configs/mq_config.json
ROUTING_SIM_MQ_CONFIG=configs/mq_config.json python -m app.app_mq_joint
ROUTING_SIM_API_CONFIG=configs/api_config.toml python -c "from app.config_loader import ConfigLoader; ConfigLoader()"
```

Do not commit machine-specific hostnames, credentials, or private network
addresses. Use local environment variables or ignored local config copies for
private deployments.

## API Notes

The historical Chinese API notes are kept in `app/api_documentation_zh.md` and
`app/mq测试用例.md`. New API documentation should be added under `docs/` and
linked from this README.

## Validation

For documentation-only changes:

```bash
git diff --check
python3 -m py_compile run.py quick_test.py quick_clean.py
```

For runtime changes, also run the Docker build and the smallest topology smoke
test that exercises the changed API path.
