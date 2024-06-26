from operator import itemgetter
from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_core.pydantic_v1 import BaseModel, Field
from src.state import GraphState

class CodeAssistantNodes:
    """Represents a collection of nodes.
    
    Attributes:
        context: A dictionary where each key is a string.
    """
    
    nodes = [
        "generate",
        "check_code_execution",
        "check_code_imports",
        "finish",
    ]
    
    def __init__(self, context: str, debug: bool = True):
        self.context = context
        self.debug = debug
        self.model = (
            "gpt-4-0125-preview" if not self.debug 
            else "gpt-3.5-turbo"
        )
        self.node_map = {
            "generate": self.generate,
            "check_code_execution": self.check_code_execution,
            "check_code_imports": self.check_code_imports,
            "finish": self.finish,
        }
    
    
    def generate(self, state: GraphState) -> GraphState:
        """
        Generate a code solution based on LCEL docs and the input question
        with optional feedback from code execution tests

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, documents, that contains retrieved documents
        """

        ## State
        state_dict = state["keys"]
        question = state_dict["question"]
        iteration = state_dict["iteration"]

        ## Data model
        class code(BaseModel):
            """Code output"""

            prefix: str = Field(
                description="Description of the problem and approach"
            )
            imports: str = Field(description="Code block import statements")
            code: str = Field(
                description="Code block not including import statements"
            )

        ## LLM
        llm = ChatOpenAI(temperature=0, 
                         model=self.model, 
                         streaming=True)

        # Tool
        code_tool_oai = convert_to_openai_tool(code)

        # LLM with tool and enforce invocation
        llm_with_tool = llm.bind(
            tools=[code_tool_oai],
            tool_choice={"type": "function", "function": {"name": "code"}},
        )

        # Parser
        parser_tool = PydanticToolsParser(tools=[code])

        ## Prompt
        template = (
            """You are a coding assistant with expertise in LCEL, LangChain expression language. \n
            You are tasked with responding to the following user question: {question}
            Your response will be shown to the user.
            Here is a full set of LCEL documentation:
            \n ------- \n
            {context}
            \n ------- \n
            Answer the user question based on the above provided documentation. \n
            Ensure any code you provide can be executed with all required imports and variables defined. \n
            Structure your answer as a description of the code solution, \n
            then a list of the imports, and then finally list the functioning code block. \n
            Here is the user question again: \n
            \n --- --- --- \n {question}
        """
        )
        
        if "error" in state_dict:
            print("---RE-GENERATE SOLUTION w/ ERROR FEEDBACK---")
            
            error = state_dict["error"]
            code_solution = state_dict["generation"]
            
            # Update prompt.
            
            addendum = """  \n --- --- --- \n You previously tried to solve this problem. \n Here is your solution:
            \n --- --- --- \n {generation}  \n --- --- --- \n  Here is the resulting error from code
            execution:  \n --- --- --- \n {error}  \n --- --- --- \n Please re-try to answer this.
            Structure your answer with a description of the code solution. \n Then list the imports.
            And finally list the functioning code block. Structure your answer with a description of
            the code solution. \n Then list the imports. And finally list the functioning code block.
            \n Here is the user question: \n --- --- --- \n {question}"""
        
            template = template + addendum
            
            prompt = PromptTemplate(
                template=template,
                input_variables=["context", "question", "generation", "error"],
            )
            
            chain = (
                {
                    "context": lambda _: self.context,
                    "question": itemgetter("question"),
                    "generation": itemgetter("generation"),
                    "error": itemgetter("error"),
                }
                | prompt
                | llm_with_tool
                | parser_tool
            )
            
            code_solution = chain.invoke(
                {
                    "question": question,
                    "generation": str(code_solution[0]),
                    "error": error,
                }
            )
        
        else:
            print("---GENERATE SOLUTION---")
            
            # Prompt
            prompt = PromptTemplate(
                template=template,
                input_variables=["context", "question"],
            )
            
            chain = (
                {
                    "context": lambda _: self.context,
                    "question": itemgetter("question"),
                }
                | prompt
                | llm_with_tool
                | parser_tool
            )
            code_solution = chain.invoke({"question": question})
            
        iteration = iteration + 1
        return {
            "keys": {
                "generation": code_solution,
                "question": question,
                "iteration": iteration,
            }
        }
        
    def check_code_imports(self, state: GraphState):
        print("---CHECKING CODE IMPORTS---")
        
        ## State
        state_dict = state["keys"]
        question = state_dict["question"]
        code_solution = state_dict["generation"]
        imports = code_solution[0].imports
        iteration = state_dict["iteration"]
        
        try:
            # Attempt to execute imports
            exec(imports)
        except Exception as e:
            print("---CODE IMPORT CHECK: FAILED---")
            error = f"Execution error: {e}"
            if "error" in state_dict:
                error_prev_runs = state_dict["error"]
                error = error_prev_runs + "\n --- Most recent run error --- \n" + error
                
        else:
            print("---CODE IMPORT CHECK: PASSED---")
            error = "None"
            
        return {
            "keys": {
                "generation": code_solution,
                "error": error,
                "iteration": iteration,
                "question": question,
            }
        }

    def check_code_execution(self, state: GraphState):
        print("---CHECKING CODE EXECUTION---")
        state_dict = state["keys"]
        question = state_dict["question"]
        code_solution = state_dict["generation"]
        prefix = code_solution[0].prefix
        imports = code_solution[0].imports
        code = code_solution[0].code
        code_block = imports + "\n" + code
        iteration = state_dict["iteration"]
        
        try:
            # Attempt to execute the code block
            exec(code_block)
        except Exception as e:
            print("---CODE BLOCK CHECK: FAILED---")
            error = f"Execution error: {e}"
            if "error" in state_dict:
                error_prev_runs = state_dict["error"]
                error = (
                    error_prev_runs 
                    + "\n --- Most recent run error --- \n" 
                    + error
                )
        else:
            print("---CODE BLOCK CHECK: PASSED---")
            error = "None"
            
        return {
            "keys": {
                "generation": code_solution,
                "question": question,
                "error": error,
                "prefix": prefix,
                "imports": imports,
                "iteration": iteration,
                "code": code,
            }
        }
        
    def finish(self, state: GraphState) -> dict:
        """
        Finish the graph

        Returns:
            dict: Final result
        """

        print("---FINISHING---")

        response = extract_response(state)

        return {"keys": {"response": response}}


def extract_response(state: GraphState) -> str:
    """
    Extract the response from the graph state

    Args:
        state (dict): The current graph state

    Returns:
        str: The response
    """

    state_dict = state["keys"]
    code_solution = state_dict["generation"][0]
    prefix = code_solution.prefix
    imports = code_solution.imports
    code = code_solution.code

    return "\n".join([prefix, imports, code])