import random


DEFAULT_COORDINATES = {"latitude": 0.0, "longitude": 0.0}


def require_positive_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 1:
        raise ValueError(f"{name} must be at least 1")
    return value


def router_node_specs(node_names):
    return [
        {"name": node_name, "type": "Router", "coordinates": dict(DEFAULT_COORDINATES)}
        for node_name in node_names
    ]


def random_router_topology(count, rng=None):
    require_positive_int("count", count)
    rng = rng or random
    nodes = [f"node_{index + 1}" for index in range(count)]
    edges = set()
    node_connections = {node: 0 for node in nodes}

    if count == 1:
        return router_node_specs(nodes), []

    max_conn = 2 if count >= 3 else count
    for node in nodes:
        possible_connections = rng.sample(nodes, k=rng.randint(1, max_conn))
        for target_node in possible_connections:
            if node == target_node:
                continue
            edge = tuple(sorted((node, target_node)))
            if edge not in edges:
                edges.add(edge)
                node_connections[node] += 1
                node_connections[target_node] += 1

    for node in nodes:
        if node_connections[node] > 0:
            continue
        while True:
            target_node = rng.choice(nodes)
            if node == target_node:
                continue
            edge = tuple(sorted((node, target_node)))
            if edge not in edges:
                edges.add(edge)
                node_connections[node] += 1
                node_connections[target_node] += 1
                break

    return router_node_specs(nodes), sorted(edges)


def circle_router_topology(count):
    require_positive_int("count", count)
    if count < 3:
        raise ValueError("count must be at least 3 for a circle topology")
    nodes = [f"node_{index + 1}" for index in range(count)]
    edges = [(nodes[index], nodes[(index + 1) % count]) for index in range(count)]
    return router_node_specs(nodes), edges


def grid_router_topology(rows, cols):
    require_positive_int("rows", rows)
    require_positive_int("cols", cols)
    nodes = [f"node_{row * cols + col + 1}" for row in range(rows) for col in range(cols)]
    edges = []
    for row in range(rows):
        for col in range(cols):
            node_index = row * cols + col
            if col < cols - 1:
                edges.append((nodes[node_index], nodes[node_index + 1]))
            if row < rows - 1:
                edges.append((nodes[node_index], nodes[node_index + cols]))
    return router_node_specs(nodes), edges
