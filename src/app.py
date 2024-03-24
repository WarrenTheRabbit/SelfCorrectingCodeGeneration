from src import agent
from langserve import add_routes
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.runnables import RunnableLambda

web_app = FastAPI(
    title="CodeAssistant",
    version="1.0",
    description="Answers questions about LCEL.",
)

web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

def serve():
    graph = agent.construct_graph(debug=True).compile()
    
    def input_(question: str) -> dict:
        return {
            "keys": {
                "question": question,
                "iteration": 0
            }
        }
        
    chain = RunnableLambda(input_) | graph
        
    add_routes(
        web_app,
        chain,
        path="/codeassistant"
    )
    
    return web_app
    
    
    
if __name__ == "__main__":
    import uvicorn
    app = serve()
    uvicorn.run(app, host="localhost", port=8000)