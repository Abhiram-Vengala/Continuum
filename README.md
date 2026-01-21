# Continuum 🧠

**Cognitive Continuity Across Your Favorite AI Chatbots**

> Never lose context again. Seamlessly maintain conversation memory across ChatGPT, Claude, Gemini, and more.

---

## 🎯 What is Continuum?

Continuum is a **structured memory management system** that captures and organizes conversation context across multiple AI platforms. It extracts semantic information from chats with ChatGPT, Claude, and Gemini, stores them in a multi-layered memory system, and provides policy-driven retrieval.

**Core capabilities:**
- ✅ Extracts structured information (decisions, facts, constraints, questions) from conversations using Groq LLM
- ✅ Stores memories in three typed layers (working, episodic, semantic) with explicit scoping
- ✅ Applies rule-based policies to determine what gets stored where
- ✅ Retrieves memories via vector similarity + recency
- ✅ Renders memory context formatted for each LLM platform

---

## 🤔 Why Continuum?

### The Problem

Users frequently switch between ChatGPT, Claude, and Gemini, but each assistant has **zero persistent memory**:

❌ Start conversation with ChatGPT about "Project X architecture"
❌ Switch to Claude for a code review
❌ "Wait, what were the constraints we discussed?"
❌ Copy-paste entire context manually
❌ Same setup for Gemini, each time

**Result**: Friction, repeated context, lost information.

### The Solution (v1)

Continuum automates the **capture and organization** of semantic information, but **NOT the retrieval**.

What you do:
1. Chat with an AI assistant normally
2. Click extension when done
3. Continuum extracts structure (decision/fact/constraint/question)
4. Stores in appropriate layer based on rules
5. On next chat, you can request context → system renders it
6. You manually copy context into next conversation

What you don't need to do:
- Manually identify "what matters"
- Manually categorize information
- Manually search across past conversations
- Re-explain the same constraints to different AIs

### Why It Matters

**Structured memory is expensive (for humans)** but **cheap (for systems)**.

Continuum shifts the burden: instead of **you** remembering and summarizing, the **system** extracts and stores. You still decide what to retrieve, but finding and formatting is automatic.

---

## 🚀 Architecture & Components

### Core System

```
Continuum
├── Backend (FastAPI + Python)
│   ├── MemoryExtractor
│   │   ├── Uses Groq LLM (llama-3.3-70b)
│   │   ├── Extracts: DECISION, FACT, CONSTRAINT, QUESTION, ASSUMPTION
│   │   ├── Confidence scoring: 0.0-1.0
│   │   └── Generates FastEmbed embeddings for semantic storage
│   │
│   ├── PolicyEngine (Rule-Based)
│   │   ├── Evaluates each extracted memory unit against 7 rules
│   │   ├── Decisions: Store location (working/episodic/semantic) or discard
│   │   ├── Detects contradictions (deprecates old decisions)
│   │   └── Currently: STATIC rules (hardcoded logic)
│   │
│   ├── MemoryStoreManager
│   │   ├── WorkingMemoryStore (in-memory dict with TTL)
│   │   ├── EpisodicMemoryStore (SQLite, immutable log)
│   │   └── SemanticMemoryStore (Qdrant, 384-dim vectors)
│   │
│   ├── ContextComposer
│   │   ├── Retrieves: all active working + last 10 episodic + top-10 semantic
│   │   └── Strategy: Fixed retrieval (not adaptive/query-aware)
│   │
│   └── ProviderRenderer
│       └── Formats composed memory for target platform
│
└── Frontend (Chrome Extension)
    ├── Content Scripts (per-platform conversation extraction)
    ├── Popup UI (user interface)
    └── Background Service Worker (orchestration)
```

### Information Flow

```
User Chat (ChatGPT/Claude/Gemini)
    ↓
[Chrome Extension] → Extract conversation text
    ↓
[Groq LLM] → Parse into semantic units with confidence
    ↓
[PolicyEngine] → Apply rules: where to store?
    ↓
[3-Layer Storage]
    ├─ Working (TTL) if: session-scoped
    ├─ Episodic (immutable) if: decision OR high-conf fact
    └─ Semantic (vector) if: high-conf OR project-scoped
    ↓
[On Next Chat] → User triggers retrieval
    ↓
[Fixed Retrieval] → Get working + recent episodic + similar semantic
    ↓
[Compose & Render] → Format for target LLM
    ↓
User includes context in new chat manually
```

**Working Memory** 🔄
- **What**: Current session context with time-to-live (TTL)
- **Stored in**: In-memory dictionary with expiration tracking
- **Lifetime**: 1 hour by default (configurable per scope)
- **Storage trigger**: Session-scoped facts, temporary information
- **Retrieval**: Only active (non-expired) memories for current session
- **Cleared**: Automatically on TTL expiration

**Episodic Memory** 📜
- **What**: Complete chronological log of all stored events
- **Stored in**: SQLite database with sequence numbers
- **Lifetime**: Permanent (write-once, immutable)
- **Storage trigger**: All decisions + high-confidence facts
- **Retrieval**: Last N events by recency (default: last 10)
- **Special**: Decisions can be marked DEPRECATED (contradicted by newer decisions)

**Semantic Memory** 🧠
- **What**: Extracted concepts + relationships as vector embeddings
- **Stored in**: Qdrant vector database (384-dim embeddings via FastEmbed)
- **Lifetime**: Permanent
- **Storage trigger**: High-confidence (>0.7) facts + project-scoped constraints
- **Retrieval**: Top-k by cosine similarity to query embedding (default: k=10)
- **No automatic conversion**: Episodic → Semantic never happens; decided by policy at extraction time

**Conversion Rules (STATIC)**
```
Type: Decision + Confidence > 0.8 → Semantic
Type: Constraint + Scope ∈ {PROJECT, GLOBAL} → Semantic
Type: Fact + Confidence > 0.7 → Semantic
Type: Decision (all) → Episodic
Type: Fact + Scope = SESSION → Working
Type: Question + Confidence < 0.5 → DISCARD
Otherwise → Working (with TTL)
```

---

## 🎯 What This System Does (Precisely)

### ✅ Implemented

1. **Structured Extraction**
   - Parses conversations into typed units (Decision, Fact, Constraint, Question, Assumption)
   - Assigns confidence scores via LLM
   - Scope tagging (session, project, global)

2. **Rule-Based Storage Routing**
   - Policy engine applies deterministic rules
   - Routes memories to correct store (working/episodic/semantic)
   - Detects contradicting decisions and marks old ones DEPRECATED

3. **Multi-Layer Storage**
   - Working: in-memory with TTL (session-scoped)
   - Episodic: SQLite append-only log (all decisions + facts)
   - Semantic: Qdrant vectors (long-term knowledge)

4. **Fixed Retrieval**
   - Working: all active memories for session
   - Episodic: last 10 by insertion order
   - Semantic: top-10 by embedding cosine similarity

5. **Platform-Specific Rendering**
   - Formats context into system prompts for ChatGPT, Claude, Gemini, Groq

### ⚠️ Current Limitations (v1)

1. **No Query-Time Intent Analysis**
   - Retrieval is fixed: always gets working + last 10 episodic + top-10 semantic
   - No: "What context is actually relevant to this new question?"
   - Future: Intent classification could reduce noise

2. **No Adaptive Policies**
   - Rules are hardcoded; policies don't learn or adapt
   - No: feedback loops, user preferences, or dynamic adjustment
   - Future: Could add user feedback to refine storage decisions

3. **No Automatic Lifecycle Management**
   - No pruning, no TTL for semantic memory, no archival
   - Memories live forever (or until manual deletion)
   - Future: Time-decay, relevance scoring, auto-archive

4. **No Conflict Resolution**
   - Contradictions are marked DEPRECATED, not resolved
   - No: merging, consensus logic, or contradiction explanation
   - Future: Multi-source validation

5. **No Cross-Session Learning**
   - Each session is independent
   - No: pattern detection, meta-insights, or long-term trends

### 📊 What You Get Today

A **foundation for memory continuity**:
- Capture: conversations → structured units ✓
- Store: rule-driven multi-layer storage ✓
- Retrieve: vector search + recency ✓
- Render: platform-specific formatting ✓

NOT yet:
- Autonomous decision-making
- Adaptive retrieval
- Self-improving policies
- Real-time conflict resolution

---

## 📦 Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Groq** - Fast LLM for context extraction
- **SQLite** - Episodic memory storage
- **Qdrant** - Vector database for semantic search
- **FastEmbed** - Efficient embedding model
- **Pydantic** - Data validation and schemas

### Frontend
- **Chrome Extension API** - Platform integration
- **Vanilla JavaScript** - Lightweight UI
- **Content Scripts** - Conversation extraction

---

## 🛠️ Installation & Setup

### Backend Setup

1. **Install Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   Create a `.env` file in the `backend` directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   SQLITE_DB_PATH=episodic_memory.db
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   ```

3. **Start Qdrant Vector Database** (Docker)
   ```bash
   docker run -p 6333:6333 qdrant/qdrant:latest
   ```

4. **Run Backend Server**
   ```bash
   uvicorn app:app --reload --port 8000
   ```
   Backend will be available at `http://localhost:8000`

### Frontend Setup

1. **Load Chrome Extension**
   - Open `chrome://extensions/`
   - Enable "Developer mode" (top right)
   - Click "Load unpacked"
   - Select the `frontend` folder

2. **Configure Extension**
   - The extension will connect to your local backend at `http://localhost:8000`

---

## 💡 How It Works

### Step-by-Step

```
1. [Capture] Chrome extension extracts raw conversation from active tab
   └─ Sends to backend via /process_conversation endpoint

2. [Extract] Groq LLM analyzes messages, identifies semantic units
   └─ Output: List of {type, content, scope, confidence}

3. [Policy Evaluation] Rule engine decides destination for each unit
   └─ Decision tree: type + confidence + scope → store location
   
4. [Storage] Memory routed to appropriate layer
   ├─ Working: in-memory, expires after TTL
   ├─ Episodic: persisted to SQLite log
   └─ Semantic: embedded via FastEmbed, stored in Qdrant

5. [Retrieval Trigger] User starts new chat, clicks extension
   └─ Backend retrieves fixed set:
      • Active working memories (current session)
      • Last 10 episodic events (by recency)
      • Top 10 semantic matches (by embedding similarity)

6. [Compose] Memory pieces assembled into ContextState object
   └─ Metadata: memory counts, breakdown by type

7. [Render] ContextState formatted per target provider
   └─ Different system prompts for ChatGPT vs Claude vs Gemini

8. [User Copies] User manually copies rendered context into new chat
   └─ Integrates memory into their prompt
```

### Memory Extraction Logic

The LLM extracts these types:

```
DECISION   (e.g., "We chose FastAPI")
FACT       (e.g., "Rate limit is 100 req/min")
CONSTRAINT (e.g., "Must support mobile")
QUESTION   (e.g., "How to handle auth?")
ASSUMPTION (e.g., "Users have stable internet")
```

Each gets:
- **confidence**: 0.0-1.0 (how certain?)
- **scope**: session (temp) | project (this work) | global (always true)
- **embedding**: 384-dim vector for semantic search

### Policy Rules (Current)

| Rule | Condition | Action |
|------|-----------|--------|
| High-confidence decisions | DECISION + conf > 0.8 | → Semantic |
| Project constraints | CONSTRAINT + scope ∈ {PROJECT, GLOBAL} | → Semantic |
| Session facts | FACT + scope = SESSION | → Working (TTL) |
| All decisions | type = DECISION | → Episodic (append) |
| Contradictions | New DECISION contradicts old | Mark old DEPRECATED |
| Low-confidence Q | QUESTION + conf < 0.5 | DISCARD |
| High-confidence facts | FACT + conf > 0.7 | → Semantic |
| Default | Everything else | → Working (TTL) |

---

## 📖 API Endpoints

### Process Conversation
```
POST /process_conversation
Content-Type: application/json

{
  "conversation_input": {
    "session_id": "session123",
    "provider": "chatgpt",
    "messages": [...]
  },
  "target_provider": "claude",
  "apply_policies": true,
  "retrieve_context": true
}
```

### Semantic Search
```
POST /semantic_search
Content-Type: application/json

{
  "query": "Tell me about the project architecture",
  "top_k": 10,
  "min_confidence": 0.5
}
```

---

## 🔮 Roadmap & Known Limitations

### Current Gaps (v1)

| Feature | Status | Impact |
|---------|--------|--------|
| Query-time intent classification | ❌ Not implemented | Retrieves all memories regardless of relevance |
| Adaptive policies | ❌ Not implemented | Rules are static, don't learn |
| TTL for semantic memory | ❌ Not implemented | Memories never expire |
| Automatic pruning | ❌ Not implemented | Storage grows unbounded |
| User feedback loop | ❌ Not implemented | System can't optimize based on feedback |
| Conflict resolution | ❌ Partial (deprecation only) | Contradictions marked but not resolved |
| Multi-session insights | ❌ Not implemented | No cross-session pattern detection |

### v2 Priorities

- [ ] **Smart Retrieval**: Classify user query intent → filter relevant context
- [ ] **Learning Policies**: Track which memories are actually used → adjust rules
- [ ] **Semantic Pruning**: Time-decay + relevance scoring → archive old facts
- [ ] **Web Dashboard**: Visualize memory graph, edit stores, debug policies
- [ ] **Feedback Integration**: User marks context as "helpful" or "irrelevant" → retrains policy
- [ ] **Multi-user Support**: Shared memory pools with access control
- [ ] **Mobile Integration**: Mobile app for on-the-go memory capture
- [ ] **Advanced Conflict Resolution**: Merge contradictions, weighted voting

---

## 📝 Project Structure

```
Context/
├── backend/
│   ├── app.py                 # FastAPI application entry point
│   ├── requirements.txt        # Python dependencies
│   └── src/
│       ├── orchestrator.py     # Central orchestration logic
│       ├── extractor_service.py # Memory extraction with LLM
│       ├── memory_stores.py    # SQLite + Qdrant management
│       ├── policy_engine.py    # Memory lifecycle policies
│       ├── context_composer.py # Context assembly & rendering
│       └── Schemas.py          # Pydantic data models
│
└── frontend/
    ├── manifest.json           # Chrome extension manifest
    ├── popup.html              # UI popup
    ├── popup.js                # Popup logic
    ├── background.js           # Service worker
    ├── icons/                  # Extension icons
    └── content-scripts/
        ├── chatgpt.js          # ChatGPT conversation extractor
        ├── claude.js           # Claude conversation extractor
        └── gemini.js           # Gemini conversation extractor
```

---

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs and suggest features via issues
- Submit pull requests with improvements
- Extend platform support for more AI assistants

---

## 🎓 Learning Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Qdrant Vector Database](https://qdrant.tech/)
- [Chrome Extension Development](https://developer.chrome.com/docs/extensions/)
- [Groq API](https://console.groq.com/)

---

## 🌟 Acknowledgments

Built with modern ML/AI technologies to solve the cognitive continuity challenge across multiple AI platforms.

---

**Made with ❤️ for AI enthusiasts and power users**
