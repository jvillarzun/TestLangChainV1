"""
graph/singleton.py
──────────────────
Instancia compartida del grafo LangGraph.
Slack webhook y control API usan el mismo checkpointer.
"""
from graph.mach_graph import build_graph, get_graph_config

_graph = build_graph()


def get_graph():
    return _graph
