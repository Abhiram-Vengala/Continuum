from pydantic import BaseModel , Field
from typing import Optional , Literal , List
from datetime import datetime , timezone
from enum import Enum
import uuid


class MemoryType(str,Enum):
    DECISION = "decision"
    FACT = "fact"
    CONSTRAINT = "constraint"
    QUESTION = "question"
    ASSUMPTION = "assumption"

class MemoryScope(str,Enum):
    SESSION = "session"
    PROJECT = "project"
    GLOBAL = "global"

class MemoryLifecycle(str,Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REINFORCED = "reinforced"

class MemoryUnit(BaseModel):
    id:str = Field(default_factory=lambda: str(uuid.uuid4()))
    type:MemoryType
    content:str
    scope:MemoryScope
    confidence: float = Field(ge=0.0, le=1.0 , default=0.7)
    lifecycle: MemoryLifecycle = MemoryLifecycle.ACTIVE
    source_session:str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    embedding: Optional[List[float]] = None
    metadata: dict = Field(default_factory=dict)

    class Config:
        use_enum_values = True

class WorkingMemoryEntry(BaseModel):
    memory_unit: MemoryUnit
    ttl_seconds: int = 3200
    expires_at: datetime

class EpisodicMemoryEntry(BaseModel):
    memory_unit: MemoryUnit
    sequence_number : int
    event_type : Literal["decision" , "transition" , "change"]

class SemanticMemoryEntry(BaseModel):
    memory_unit : MemoryUnit
    embedding : List[float]
    retrieval_count : int = 0
    last_retrieved : Optional[datetime] = None

class PolicyDecision(BaseModel):
    should_store: bool
    target_store : Optional[Literal["working" , "episodic" , "semantic"]]
    confidence_override: Optional[float] = None
    deprecate_existing: List[str] = Field(default_factory=list)
    reason: str

class PolicyRule(BaseModel):
    name:str
    condition: str
    action: str
    priority: int =0

class ConversationInput(BaseModel):
    session_id: str
    project_id: Optional[str] = None
    user_message: str
    conversation_history: List[dict] = Field(default_factory=list)
    intent: Optional[str] = None

class ExtractionRequest(BaseModel):
    conversation_input: ConversationInput
    extraction_mode: Literal["full","incremental"] = "incremental"

class ExtractionResult(BaseModel):
    memory_units: List[MemoryUnit]
    extraction_metadata: dict = Field(default_factory=dict)

class RetrievalRequest(BaseModel):
    session_id:str
    project_id: Optional[str] = None
    query:str
    max_results: int = 10
    scope_filter: Optional[List[MemoryScope]] = None
    type_filter: Optional[List[MemoryScope]] = None

class RetrievalResult(BaseModel):
    working_memories: List[MemoryUnit]
    episodic_memories: List[MemoryUnit]
    semantic_memories: List[MemoryUnit]
    retrieval_metadata: dict = Field(default_factory=dict)

class ContextState(BaseModel):
    session_id: str
    working_memory: List[MemoryUnit]
    episodic_memory: List[MemoryUnit]
    semantic_memory: List[MemoryUnit]
    user_message: str
    metadata: dict = Field(default_factory=dict)

class LLMProvider(str,Enum):
    CHATGPT = "chatgpt"
    CLAUDE = "claude"
    GEMINI = "gemini"
    GROQ = "groq"

class RenderRequest(BaseModel):
    context_state: ContextState
    provider: LLMProvider
    model: Optional[str] = None

class RenderResult(BaseModel):
    provider: LLMProvider
    system_prompt: Optional[str] = None
    user_prompt: str
    messages: Optional[List[dict]] = None
    metadata: dict = Field(default_factory=dict)

class ProcessConversationRequest(BaseModel):
    conversation_input : ConversationInput
    retrieve_context: bool = True
    target_provider: LLMProvider = LLMProvider.GROQ
    apply_policies: bool = True

class ProcessConversationResponse(BaseModel):
    rendered_context: RenderResult
    stored_memories: List[MemoryUnit]
    policy_decisions: List[PolicyDecision]
    metadata: dict = Field(default_factory=dict)

