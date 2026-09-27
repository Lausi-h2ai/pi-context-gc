import heapq


def build_order(graph):
    """Return the lexicographically smallest topological ordering of graph."""
    nodes = set(graph)
    for prerequisites in graph.values():
        nodes.update(prerequisites)

    dependents = {node: [] for node in nodes}
    indegree = {node: 0 for node in nodes}

    for node, prerequisites in graph.items():
        for prerequisite in set(prerequisites):
            dependents[prerequisite].append(node)
            indegree[node] += 1

    ready = [node for node in nodes if indegree[node] == 0]
    heapq.heapify(ready)
    order = []

    while ready:
        node = heapq.heappop(ready)
        order.append(node)
        for dependent in dependents[node]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(ready, dependent)

    if len(order) != len(nodes):
        raise ValueError("graph contains a cycle")
    return order
