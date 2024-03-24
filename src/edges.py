from src.state import GraphState
from langgraph.graph import StateGraph
from src.nodes import CodeAssistantNodes
from typing import Callable

EXPECTED_NODES = CodeAssistantNodes.nodes

class CodeAssistantEdges:

    @classmethod
    def connect(cls, graph) -> StateGraph:
        
        for node_name in set(EXPECTED_NODES):
            assert node_name in graph.nodes, f"Node {node_name} not found in graph"
            
        graph.add_edge("generate", "check_code_imports")
        
        graph.add_conditional_edges(
            "check_code_imports",
            cls.EDGE_MAP["decide_to_check_code_exec"],
            {
                "generate": "generate",
                "check_code_execution": "check_code_execution",
                "finish": "finish",
            }
        )
        graph.add_conditional_edges(
            "check_code_execution",
            cls.EDGE_MAP["decide_to_finish"],
            {
                "finish": "finish",
                "generate": "generate"
            }
        )
        return graph
        
    @staticmethod
        
    @staticmethod
    def decide_to_finish(state: GraphState) -> str:
        """
        Determines whether to finish (re-try code 3 times).

        Args:
            state (dict): The current graph state

        Returns:
            str: Next node to call
        """

        print("---DECIDE TO TEST CODE EXECUTION---")
        state_dict = state["keys"]
        error = state_dict["error"]
        iteration = state_dict["iteration"]

        if error == "None":
            print("---DECISION: TERMINATE - SOLUTION FOUND---")
            return "finish"
        elif iteration >= 3:
            print("---DECISION: TERMINATE - TOO MANY TRIES---")
            return 'finish'
        else:
            print("---DECISION: RE-TRY SOLUTION---")
            return "generate"

    @staticmethod
    def decide_to_check_code_exec(state: GraphState) -> str:
        
        print("---DECIDE TO TEST CODE EXECUTION---")
        state_dict = state["keys"]
        error = state_dict["error"]
        iteration = state_dict['iteration']
        
        if error == "None":
            print("---DECISION: TEST CODE EXECUTION---")
            return "check_code_execution"
        elif iteration >= 3:
            print("---DECISION: TERMINATE - TOO MANY TRIES---")
            return 'finish'
        else:
            print("---DECISION: RE-TRY SOLUTION---")
            return "generate"


    EDGE_MAP: dict[str, Callable] = {
        "decide_to_check_code_exec": decide_to_check_code_exec,
        "decide_to_finish": decide_to_finish,
    }