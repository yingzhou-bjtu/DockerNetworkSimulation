'''Normalize and validate a simulated-topology start request.

The configured-service Flask and RabbitMQ paths both drive
`app.network_api_handler.NetworkAPIHandler`, so accepting the same boundary
here keeps request parsing testable without touching Docker. The joint MQ
service keeps its separate topology/config protocol.
'''
from __future__ import annotations

from dataclasses import dataclass


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
