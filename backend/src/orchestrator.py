from typing import List , Optional
from datetime import datetime , timezone
import traceback

from src.Schemas import (
    ConversationInput, MemoryLifecycle, ProcessConversationResponse,
    ContextState, LLMProvider, RenderRequest,
    PolicyDecision, MemoryUnit, MemoryType
)
from src.memory_stores import MemoryStoreManager
from src.policy_engine import MemoryPolicyEngine
from src.extractor_service import MemoryExtractor
from src.context_composer import ContextComposer, ProviderRenderer

class ContextOrchestrator:
    def __init__(
        self,
        groq_api_key: str = None,
        sqlite_db_path: str = "episodic_memory.db",
        # Qdrant config
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        qdrant_collection: str = "semantic_memory",
        vector_size: int = 384
    ):
        self.memory_store = MemoryStoreManager(
            sqlite_db_path=sqlite_db_path,
            qdrant_host=qdrant_host,
            qdrant_port=qdrant_port,
            qdrant_collection=qdrant_collection,
            vector_size=vector_size
        )
        self.policy_engine = MemoryPolicyEngine()
        self.extractor = MemoryExtractor(api_key=groq_api_key)
        self.composer = ContextComposer()
        self.renderer = ProviderRenderer()

    async def process_conversation(
        self,
        conversation_input:ConversationInput,
        target_provider:LLMProvider = LLMProvider.GROQ,
        apply_polices:bool = True,
        retrieve_context: bool = True
    ) -> ProcessConversationResponse:
        stored_memories : List[MemoryUnit] = []
        policy_decisions : List[PolicyDecision] = []

        try:
            print("DEBUG: Starting extraction...")
            extraction_result = self.extractor.extract(conversation_input)
            print(f"DEBUG: Extracted {len(extraction_result.memory_units)} memory units")
            
            if apply_polices and extraction_result.memory_units:
                print("DEBUG: Getting existing memories...")
                existing_memories = self.memory_store.get_all_memories(conversation_input.session_id)
                
                for i, memory_unit in enumerate(extraction_result.memory_units):
                    print(f"DEBUG: Processing memory unit {i+1}/{len(extraction_result.memory_units)}")
                    print(f"  Type: {memory_unit.type}, Type class: {type(memory_unit.type)}")
                    print(f"  Content: {memory_unit.content[:50]}...")
                    
                    decision = self.policy_engine.evaluate(
                        memory_unit,
                        existing_memories
                    )
                    policy_decisions.append(decision)
                    
                    if decision.should_store:
                        print(f"  Storing in: {decision.target_store}")
                        self._store_memory(memory_unit,decision)
                        stored_memories.append(memory_unit)
                    
                    for deprecated_id in decision.deprecate_existing:
                        self.memory_store.semantic.deprecate(deprecated_id)
                        memory_unit.lifecycle = MemoryLifecycle.DEPRECATED
                        memory_unit.metadata["deprecated_reason"] = decision.reason
            
            working_memories = []
            episodic_memories = []
            semantic_memories = []

            if retrieve_context :
                print("DEBUG: Retrieving context...")
                working_memories = self.memory_store.working.get_active(
                    conversation_input.session_id
                )
                episodic_memories = self.memory_store.episodic.get_recent(limit=10)

                if conversation_input.user_message:
                    query_embedding = self.extractor.generate_embedding(conversation_input.user_message)
                    semantic_memories = self.memory_store.semantic.search(query_embedding,top_k=10)
            
            print("DEBUG: Composing context...")
            context_state = self.composer.compose(
                session_id=conversation_input.session_id,
                user_message=conversation_input.user_message,
                working_memories=working_memories,
                episodic_memories=episodic_memories,
                semantic_memories=semantic_memories
            )
            
            print("DEBUG: Rendering context...")
            render_request = RenderRequest(
                context_state=context_state,
                provider=target_provider
            )
            rendered_context = self.renderer.render(render_request)

            print("DEBUG: Process completed successfully")
            return ProcessConversationResponse(
                rendered_context=rendered_context,
                stored_memories=stored_memories,
                policy_decisions=policy_decisions,
                metadata={
                    "extraction_metadata": extraction_result.extraction_metadata,
                    "total_memories_stored": len(stored_memories),
                    "context_composed": True,
                    "memory_breakdown": context_state.metadata.get("memory_breakdown", {})
                }
            )
        except Exception as e:
            print(f"DEBUG: ERROR occurred!")
            print(f"Error type: {type(e)}")
            print(f"Error message: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            raise
    
    def _store_memory(self,memory_unit: MemoryUnit , decision:PolicyDecision):
        try:
            print(f"    _store_memory called for: {decision.target_store}")
            if decision.target_store == "working":
                ttl = self.policy_engine.get_ttl_for_scope(memory_unit.scope)
                self.memory_store.working.add(memory_unit , ttl_seconds=ttl)
            elif decision.target_store == "episodic":
                # Check type
                print(f"    memory_unit.type = {memory_unit.type}")
                print(f"    type(memory_unit.type) = {type(memory_unit.type)}")
                print(f"    MemoryType.DECISION = {MemoryType.DECISION}")
                print(f"    Comparison result: {memory_unit.type == MemoryType.DECISION}")
                
                event_type = "decision" if memory_unit.type == MemoryType.DECISION else "event"
                print(f"    event_type = {event_type}")
                self.memory_store.episodic.add(memory_unit , event_type=event_type)
            elif decision.target_store == "semantic":
                embedding = self.extractor.generate_embedding(memory_unit.content)
                self.memory_store.semantic.add(memory_unit , embedding)
            
            if decision.confidence_override is not None:
                memory_unit.confidence = decision.confidence_override
            
            print(f"    _store_memory completed successfully")
        except Exception as e:
            print(f"    ERROR in _store_memory: {e}")
            traceback.print_exc()
            raise
    
    def get_memory_stats(self,session_id:str) -> dict:
        working = self.memory_store.working.get_active(session_id)
        episodic = self.memory_store.episodic.get_session_timeline(session_id)
        
        # Get semantic count (approximate)
        semantic_count = len(
            self.memory_store.semantic.client.scroll(
                collection_name=self.memory_store.semantic.collection_name,
                limit=1
            )[0]
        )
        
        return {
            "session_id": session_id,
            "working_memory_count": len(working),
            "episodic_memory_count": len(episodic),
            "total_semantic_memories": semantic_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }