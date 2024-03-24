from typing import TypedDict, Dict

from src import retrieval
from src.state import GraphState
from src import nodes, edges
from langgraph.graph import StateGraph


def construct_graph(debug: bool = True) -> StateGraph:
    
    context = retrieval.retrieve_docs(debug=True)
    graph = StateGraph(GraphState)
    
    # attach nodes
    graph_nodes = nodes.CodeAssistantNodes(context, debug=True)
    for key, value in graph_nodes.node_map.items():
        graph.add_node(key, value)

    # add edges
    graph = edges.CodeAssistantEdges.connect(graph)    
    graph.set_entry_point(key="generate")
    graph.set_finish_point(key="finish")
    
    return graph