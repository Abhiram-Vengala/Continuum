"""
Agentic Memory Backend - Usage Examples
"""
import requests
import json


# ────────────────────────────────────────────────────────────
# SETUP
# ────────────────────────────────────────────────────────────

BASE_URL = "http://localhost:8000"
SESSION_ID = "user_session_123"
PROJECT_ID = "project_abc"


# ────────────────────────────────────────────────────────────
# EXAMPLE 1: Process a conversation
# ────────────────────────────────────────────────────────────

def example_process_conversation():
    """
    Main workflow: Send conversation, get enriched context back.
    """
    
    payload = {
        "conversation_input": {
            "session_id": SESSION_ID,
            "project_id": PROJECT_ID,
            "user_message": "We need to build an API that handles 10k requests per second. It should use PostgreSQL for persistence and Redis for caching.",
            "conversation_history": [
                {
                    "role": "user",
                    "content": "I'm building a high-traffic e-commerce platform"
                },
                {
                    "role": "assistant",
                    "content": "What are your main technical requirements?"
                }
            ],
            "intent": "Define system architecture"
        },
        "retrieve_context": True,
        "target_provider": "groq",
        "apply_policies": True
    }
    
    response = requests.post(
        f"{BASE_URL}/api/process",
        json=payload
    )
    
    result = response.json()
    
    # Debug: Print status and full response
    print(f"Status Code: {response.status_code}")
    print(f"Response: {result}")
    
    if response.status_code != 200:
        print(f"ERROR: {result}")
        return result
    
    print("=" * 60)
    print("RENDERED CONTEXT FOR GROQ:")
    print("=" * 60)
    print("\nSYSTEM PROMPT:")
    print(result["rendered_context"]["system_prompt"])
    print("\nUSER PROMPT:")
    print(result["rendered_context"]["user_prompt"])
    
    print("\n" + "=" * 60)
    print("STORED MEMORIES:")
    print("=" * 60)
    for memory in result["stored_memories"]:
        print(f"\n[{memory['type'].upper()}] ({memory['scope']})")
        print(f"Content: {memory['content']}")
        print(f"Confidence: {memory['confidence']}")
    
    print("\n" + "=" * 60)
    print("POLICY DECISIONS:")
    print("=" * 60)
    for decision in result["policy_decisions"]:
        print(f"\nShould Store: {decision['should_store']}")
        print(f"Target Store: {decision['target_store']}")
        print(f"Reason: {decision['reason']}")
    
    return result


# ────────────────────────────────────────────────────────────
# EXAMPLE 2: Check memory statistics
# ────────────────────────────────────────────────────────────

def example_get_stats():
    """Get memory stats for a session"""
    
    response = requests.get(
        f"{BASE_URL}/api/memory/stats/{SESSION_ID}"
    )
    
    stats = response.json()
    print("\n" + "=" * 60)
    print("MEMORY STATISTICS:")
    print("=" * 60)
    print(json.dumps(stats, indent=2))
    
    return stats


# ────────────────────────────────────────────────────────────
# EXAMPLE 3: Retrieve working memory
# ────────────────────────────────────────────────────────────

def example_get_working_memory():
    """Get active working memory"""
    
    response = requests.get(
        f"{BASE_URL}/api/v1/memory/working/{SESSION_ID}"
    )
    
    data = response.json()
    print("\n" + "=" * 60)
    print("WORKING MEMORY:")
    print("=" * 60)
    
    for memory in data["memories"]:
        print(f"\n{memory['content']}")
        print(f"  Type: {memory['type']}, Scope: {memory['scope']}")
    
    return data


# ────────────────────────────────────────────────────────────
# EXAMPLE 4: Search semantic memory
# ────────────────────────────────────────────────────────────

def example_semantic_search():
    """Search semantic memory by query"""
    
    payload = {
        "query": "What database decisions have we made?",
        "top_k": 5,
        "min_confidence": 0.6
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/memory/semantic/search",
        json=payload
    )
    
    data = response.json()
    print("\n" + "=" * 60)
    print("SEMANTIC SEARCH RESULTS:")
    print("=" * 60)
    
    for memory in data["results"]:
        print(f"\n[{memory['type']}] {memory['content']}")
        print(f"  Confidence: {memory['confidence']}")
    
    return data


# ────────────────────────────────────────────────────────────
# EXAMPLE 5: Get episodic timeline
# ────────────────────────────────────────────────────────────

def example_get_episodic():
    """Get decision timeline"""
    
    response = requests.get(
        f"{BASE_URL}/api/v1/memory/episodic/{SESSION_ID}?limit=10"
    )
    
    data = response.json()
    print("\n" + "=" * 60)
    print("DECISION TIMELINE:")
    print("=" * 60)
    
    for i, memory in enumerate(data["memories"], 1):
        print(f"\n{i}. {memory['content']}")
        print(f"   Created: {memory['created_at']}")
    
    return data


# ────────────────────────────────────────────────────────────
# EXAMPLE 6: Multi-turn conversation with memory
# ────────────────────────────────────────────────────────────

def example_multi_turn():
    """Demonstrate cognitive continuity across turns"""
    
    turns = [
        "We're building a real-time chat application",
        "It needs to support 100k concurrent connections",
        "We decided to use WebSockets with Redis pub/sub",
        "What message queue should we use for background jobs?"
    ]
    
    conversation_history = []
    
    for turn in turns:
        print(f"\n{'='*60}")
        print(f"USER: {turn}")
        print('='*60)
        
        payload = {
            "conversation_input": {
                "session_id": SESSION_ID,
                "user_message": turn,
                "conversation_history": conversation_history
            },
            "target_provider": "groq",
            "retrieve_context": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/process",
            json=payload
        )
        
        result = response.json()
        
        # Show what memories were stored
        if result["stored_memories"]:
            print("\nNEW MEMORIES STORED:")
            for mem in result["stored_memories"]:
                print(f"  • [{mem['type']}] {mem['content']}")
        
        # Show composed context
        print("\nCONTEXT BREAKDOWN:")
        print(f"  Working: {result['metadata']['memory_breakdown']['working']}")
        print(f"  Episodic: {result['metadata']['memory_breakdown']['episodic']}")
        print(f"  Semantic: {result['metadata']['memory_breakdown']['semantic']}")
        
        # Add to conversation history
        conversation_history.append({
            "role": "user",
            "content": turn
        })
        conversation_history.append({
            "role": "assistant",
            "content": f"[System processed with {len(result['stored_memories'])} memories]"
        })


# ────────────────────────────────────────────────────────────
# RUN EXAMPLES
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🧠 AGENTIC MEMORY BACKEND - USAGE EXAMPLES\n")
    
    # Example 1: Basic processing
    # print("\n### EXAMPLE 1: Process Conversation ###")
    # example_process_conversation()
    
    # Example 2: Stats
    print("\n### EXAMPLE 2: Memory Stats ###")
    example_get_stats()
    
    # # Example 3: Working memory
    # print("\n### EXAMPLE 3: Working Memory ###")
    # example_get_working_memory()
    
    # # Example 4: Semantic search
    # print("\n### EXAMPLE 4: Semantic Search ###")
    # example_semantic_search()
    
    # # Example 5: Episodic timeline
    # print("\n### EXAMPLE 5: Episodic Timeline ###")
    # example_get_episodic()
    
    # # Example 6: Multi-turn
    # print("\n### EXAMPLE 6: Multi-turn Conversation ###")
    # example_multi_turn()