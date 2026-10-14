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
├── scripts/                     # smoke, cleanup, scenario, and conversion helpers
├── src/                         # topology and simulation primitives
├── app/                         # REST/RabbitMQ APIs and typed runtime config
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

The default `joint-mq` mode keeps the integrated RabbitMQ control path. To use
the TOML-defined Flask/RabbitMQ service combination, run:

```bash
python run.py --mode configured --config configs/api_config.toml
```

Use a non-default MQ configuration:

```bash
python run.py --config configs/mq_config.json
```

Run the Vire/BJTU MQ client against the TOML-defined RabbitMQ endpoint:

```bash
python mq_tool.py
ROUTING_SIM_API_CONFIG=configs/api_config.toml python mq_tool.py
```

Run a local smoke check:

```bash
python -m scripts.quick_test
python -m scripts.quick_test --nodes 6 --msmr 2 --xtr-edge node_2:xtr_a
```

`--xtr-edge` router names must refer to generated circle-router nodes such as
`node_1`, while xTR names must be unique and must not collide with router names.

Clean generated containers and networks:

```bash
python -m scripts.quick_clean
```

Convert the bundled Chinese static topology fixture to pinyin:

```bash
python -m scripts.convert_topology_to_pinyin --input configs/static_topo.json --output configs/static_topo_pinyin.json
```

Conversion output must be a JSON file, must not overwrite the input topology,
and must be written under `configs/` or `output/` when the destination is inside
this repository. Generated topology and LISP files are written under `output/`.

## Configuration

- `configs/api_config.toml`: REST API configuration.
- `configs/mq_config.json`: RabbitMQ host, queue, and exchange settings.
- `configs/macvlan_configs.json`: macvlan-related host networking settings.
- `configs/static_topo*.json`: static topology examples.

RabbitMQ settings are normalized in `app/rabbitmq_config.py` before handlers
open network connections. The TOML-defined service path uses
`StandardRabbitMQConfig`, the Vire/BJTU client derives `VireClientConfig` from
that same service config, and the JSON-defined joint MQ path uses
`JointRabbitMQConfig`. Connection fields such as hosts, exchanges, and queue
names are validated at the typed configuration boundary so empty values fail
before the service attempts a RabbitMQ connection. Flask service settings are
validated through `FlaskConfig`, so invalid ports, empty hosts, or non-boolean
debug values fail before the API thread is launched.

Topology planning is kept in `src/topology.py`, while Docker network creation
is isolated behind `src/docker_backend.py`. Unit tests can exercise topology
state with an injected in-memory network backend, and real container runs only
touch the Docker SDK when a Docker operation is executed. Topology planners
validate dimensions before allocating Docker resources: random topologies need
a positive node count, circle topologies need at least three nodes, and grid
topologies need positive row and column counts.

Runtime configuration can be supplied with explicit paths or environment
variables:

```bash
python run.py --config configs/mq_config.json
ROUTING_SIM_MQ_CONFIG=configs/mq_config.json python -m app.app_mq_joint
ROUTING_SIM_API_CONFIG=configs/api_config.toml python -c "from app.config_loader import ConfigLoader; ConfigLoader()"
```

Generated topology, LISP, and forwarding artifacts default to `output/`.
Override them with `ROUTING_SIM_OUTPUT_DIR` or the `NetworkSimulation` /
`NetworkAPIHandler` `output_dir` argument. The macvlan config directory
defaults to `configs/` and can be overridden with `ROUTING_SIM_CONFIG_DIR`.

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
python3 -m py_compile run.py mq_tool.py scripts/*.py app/config_loader.py app/rabbitmq_config.py app/app_mq.py app/app_mq_joint.py app/mq_api_handler.py app/service_runner.py
python3 -m py_compile src/docker_backend.py src/topology.py src/network_simulation.py src/nodes.py src/paths.py
python3 -m pytest tests/test_mq_tool_config.py tests/test_topology_planning.py tests/test_script_helpers.py
```

For runtime changes, also run the Docker build and the smallest topology smoke
test that exercises the changed API path.
