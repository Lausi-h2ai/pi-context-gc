import heapq


def build_order(graph):
    nodes = set(graph)
    for prerequisites in graph.values():
        nodes.update(prerequisites)

    indegree = {node: 0 for node in nodes}
    dependents = {node: [] for node in nodes}

    for node, prerequisites in graph.items():
        # A set prevents repeated prerequisite edges from affecting indegrees.
        for prerequisite in set(prerequisites):
            indegree[node] += 1
            dependents[prerequisite].append(node)

    ready = [node for node, degree in indegree.items() if degree == 0]
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
