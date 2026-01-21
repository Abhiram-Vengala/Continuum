from fastapi import FastAPI , HTTPException , Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List , Optional
from pydantic import BaseModel
from uuid import UUID
import os
import logging 
from src.orchestrator import ContextOrchestrator
from dotenv import load_dotenv
from src.Schemas import ( ConversationInput, ProcessConversationRequest, ProcessConversationResponse, LLMProvider)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"


logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(
    title="Agentic memory Backend",
    description="Congitive continuity for OpenAI , Claude , Gemini ",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator: Optional[ContextOrchestrator] = None

class SemanticSearchRequest(BaseModel):
    query:str
    top_k:int=10
    min_confidence:float = 0.5


def get_orchestrator() -> ContextOrchestrator:
    global orchestrator
    if orchestrator is None :
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key :
            raise HTTPException(status_code=500, detail="")
        orchestrator = ContextOrchestrator(
            groq_api_key=groq_api_key,
            sqlite_db_path=os.getenv("SQLITE_DB_PATH", "episodic_memory.db"),
            qdrant_host=os.getenv("QDRANT_HOST", "localhost"),
            qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
            qdrant_collection=os.getenv("QDRANT_COLLECTION", "semantic_memory"),
            vector_size=int(os.getenv("VECTOR_SIZE", "384"))
        )
    return orchestrator



@app.get("/")
async def root():
    return{
        "service": "Agentic Memory Backend (Production)",
        "status": "operational",
        "version": "2.0.0",
        "storage": {
            "working_memory": "Redis",
            "episodic_memory": "SQLite",
            "semantic_memory": "Qdrant"
        }
    }

@app.get("/health")
async def health_check(
    orch: ContextOrchestrator = Depends(get_orchestrator)
):
    """Detailed health check of all subsystems"""
    health = orch.memory_store.health_check()
    
    overall_healthy = all(health.values())
    status_code = 200 if overall_healthy else 503
    
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "subsystems": health
    }

@app.post("/api/process" , response_model=ProcessConversationResponse)
async def process_conversation(request: ProcessConversationRequest , orch:ContextOrchestrator = Depends(get_orchestrator)):
    try:
        response = await orch.process_conversation(
            conversation_input=request.conversation_input,
            target_provider=request.target_provider,
            apply_polices=request.apply_policies,
            retrieve_context=request.retrieve_context
        )
        print("Process conversation response:", response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500,detail= f"Processing error: {str(e)}")

@app.get("/api/memory/stats/{session_id}")
async def get_memory_stat(session_id:str , orch : ContextOrchestrator = Depends(get_orchestrator)):
    try:
        stats = orch.get_memory_stats(session_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Stats error: {str(e)}")

@app.get("/api/memory/working/{session_id}")
async def get_working_memory(session_id:str , orch : ContextOrchestrator = Depends(get_orchestrator)):
    try:
        memories = orch.memory_store.working.get_active(session_id)
        return{
            "session_id":session_id,
            "memories":[mem.model_dump() for mem in memories]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Retrieval error: {str(e)}"
        )

@app.get("/api/memory/episodic/{session_id}")
async def get_episodic_memory(session_id:str,limit:int = 20 , orch:ContextOrchestrator=Depends(get_orchestrator)):
    try:
        memories = orch.memory_store.episodic.get_session_timeline(session_id)
        memories = memories[-limit] if len(memories) > limit else memories
        return{
            "session_id":session_id,
            "memories":[mem.model_dump() for mem in memories]
        }
    except Exception as e:
        raise HTTPException(status_code=500 , detail=f"Retrieval error: {str(e)}")

@app.get("/api/memory/semantic/search")
async def search_semantic_memory(request:SemanticSearchRequest,orch:ContextOrchestrator= Depends(get_orchestrator)):
    try:
        query_embedding = orch.extractor.generate_embedding(request.query)
        memories = orch.memory_store.semantic.search(
            query_embedding,
            top_k = request.top_k,
            min_confidence=request.min_confidence
        )
        return{
            "query":request.query,
            "results":[mem.model_dump() for mem in memories]
        }
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Search error: {str(e)}")
    
@app.delete("/api/memory/deprecate/{memory_id}")
async def deprecate_memory(memory_id:str,orch:ContextOrchestrator=Depends(get_orchestrator)):
    try:
        orch.memory_store.semantic.deprecate(memory_id)
        return {
            "memory_id": memory_id,
            "status": "deprecated"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Deprecation error: {str(e)}"
        )

@app.post("/api/memory/reinforce/{memory_id}")
async def reinforce_memory(
    memory_id:str,
    confidence_boost:float = 0.1,
    orch:ContextOrchestrator=Depends(get_orchestrator)
):
    try:
        orch.memory_store.semantic.reinforce(memory_id,confidence_boost)
        return{
            "memory_id": memory_id,
            "status": "reinforced"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Reinforcement error: {str(e)}"
        )
    
@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    print("🧠 Agentic Memory Backend starting...")
    print("✓ Orchestrator ready")
    print("✓ Memory subsystems initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("🧠 Agentic Memory Backend shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

    
