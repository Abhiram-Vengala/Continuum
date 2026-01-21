"""Quick test of the API endpoint"""
import asyncio
from src.orchestrator import ContextOrchestrator
from src.Schemas import ConversationInput, LLMProvider, ProcessConversationRequest

async def test():
    try:
        # Create orchestrator
        orch = ContextOrchestrator(
            groq_api_key="dummy_key",
            sqlite_db_path="episodic_memory.db",
            qdrant_host="localhost",
            qdrant_port=6333,
            qdrant_collection="semantic_memory",
            vector_size=384
        )
        
        # Create request
        conv_input = ConversationInput(
            session_id="user_session_123",
            project_id="project_abc",
            user_message="We need to build an API that handles 10k requests per second.",
            conversation_history=[
                {"role": "user", "content": "I'm building a high-traffic e-commerce platform"},
                {"role": "assistant", "content": "What are your main technical requirements?"}
            ],
            intent="Define system architecture"
        )
        
        # Call process_conversation
        response = await orch.process_conversation(
            conversation_input=conv_input,
            target_provider=LLMProvider.GROQ,
            apply_polices=True,
            retrieve_context=True
        )
        
        print("SUCCESS!")
        print(f"Response type: {type(response)}")
        print(f"Has rendered_context: {hasattr(response, 'rendered_context')}")
        print(f"Response keys: {response.model_dump().keys()}")
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}")
        print(f"Message: {str(e)}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
