import heapq


def build_order(graph):
    """Return the lexicographically smallest topological ordering of graph."""
    nodes = set(graph)
    for prerequisites in graph.values():
        nodes.update(prerequisites)

    dependents = {node: [] for node in nodes}
    remaining = {node: 0 for node in nodes}
    for node, prerequisites in graph.items():
        unique_prerequisites = set(prerequisites)
        remaining[node] = len(unique_prerequisites)
        for prerequisite in unique_prerequisites:
            dependents[prerequisite].append(node)

    ready = [node for node, count in remaining.items() if count == 0]
    heapq.heapify(ready)
    order = []

    while ready:
        node = heapq.heappop(ready)
        order.append(node)
        for dependent in dependents[node]:
            remaining[dependent] -= 1
            if remaining[dependent] == 0:
                heapq.heappush(ready, dependent)

    if len(order) != len(nodes):
        raise ValueError("graph contains a cycle")
    return order
