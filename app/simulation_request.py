'''Normalize and validate a simulated-topology start request.

The configured-service Flask and RabbitMQ paths both drive
`app.network_api_handler.NetworkAPIHandler`, so accepting the same boundary
here keeps request parsing testable without touching Docker. The joint MQ
service keeps its separate topology/config protocol.
'''
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping


TOPOLOGY_TYPES = ('static', 'random')
LISP_MODES = ('none', 'simulation', 'real')


@dataclass(frozen=True)
class SimulationRequest:
    topology_type: str
    static_topology: dict | None = None
    node_count: int | None = None
    lisp_mode: str = 'none'
    xtr_count: int | None = None
    ms_count: int | None = None
    use_static_routes: bool = False


def parse_simulation_request(data):
    if not isinstance(data, dict):
        raise ValueError('simulation request must be a JSON object')

    topology_type = data.get('topology_type')
    if topology_type not in TOPOLOGY_TYPES:
        raise ValueError('topology_type must be static or random')

    static_topology = None
    node_count = None
    if topology_type == 'static':
        static_topology = data.get('static_topology')
        if not isinstance(static_topology, dict):
            raise ValueError('static topology requires a static_topology object')
        static_topology = validate_static_topology(static_topology)
    else:
        node_count = data.get('node_count')
        if isinstance(node_count, bool) or not isinstance(node_count, int) or node_count < 1:
            raise ValueError('random topology requires a positive integer node_count')

    lisp_mode = data.get('lisp_mode', 'none')
    if lisp_mode not in LISP_MODES:
        raise ValueError('lisp_mode must be none, simulation, or real')

    xtr_count = None
    ms_count = None
    if lisp_mode == 'simulation':
        xtr_count = data.get('xtr_count')
        ms_count = data.get('ms_count')
        if isinstance(xtr_count, bool) or not isinstance(xtr_count, int) or xtr_count < 1:
            raise ValueError('lisp simulation requires a positive integer xtr_count')
        if isinstance(ms_count, bool) or not isinstance(ms_count, int) or ms_count < 1:
            raise ValueError('lisp simulation requires a positive integer ms_count')

    use_static_routes = data.get('use_static_routes', False)
    if not isinstance(use_static_routes, bool):
        raise ValueError('use_static_routes must be a boolean')

    return SimulationRequest(
        topology_type=topology_type,
        static_topology=static_topology,
        node_count=node_count,
        lisp_mode=lisp_mode,
        xtr_count=xtr_count,
        ms_count=ms_count,
        use_static_routes=use_static_routes,
    )


def validate_static_topology(topology: Mapping) -> dict:
    nodes = topology.get('nodes')
    edges = topology.get('edges')
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("static_topology.nodes must be a non-empty list")
    if not isinstance(edges, list):
        raise ValueError("static_topology.edges must be a list")

    node_names: set[str] = set()
    normalized_nodes = []
    for index, node in enumerate(nodes):
        if not isinstance(node, Mapping):
            raise ValueError(f"static_topology.nodes[{index}] must be an object")
        name = node.get('name')
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"static_topology.nodes[{index}].name must be a non-empty string"
            )
        if name in node_names:
            raise ValueError(f"duplicate static topology node name: {name}")
        coordinates = node.get('coordinates')
        if not isinstance(coordinates, Mapping):
            raise ValueError(
                f"static_topology.nodes[{index}].coordinates must be an object"
            )
        node_names.add(name)
        normalized_nodes.append(dict(node))

    normalized_edges = []
    for index, edge in enumerate(edges):
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            raise ValueError(
                f"static_topology.edges[{index}] must contain two node names"
            )
        source, target = edge
        if not isinstance(source, str) or not isinstance(target, str):
            raise ValueError(
                f"static_topology.edges[{index}] endpoints must be strings"
            )
        if source == target:
            raise ValueError(
                f"static_topology.edges[{index}] must not be a self-loop"
            )
        unknown = {source, target} - node_names
        if unknown:
            raise ValueError(
                f"static_topology.edges[{index}] references unknown nodes: "
                + ", ".join(sorted(unknown))
            )
        normalized_edges.append([source, target])

    return {'nodes': normalized_nodes, 'edges': normalized_edges}
