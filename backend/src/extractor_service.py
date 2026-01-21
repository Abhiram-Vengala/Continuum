from typing import List 
from groq import Groq
import json 
import os

from src.Schemas import (
    MemoryUnit , MemoryType , MemoryScope , MemoryLifecycle,
    ConversationInput , ExtractionResult
)
from fastembed import TextEmbedding

class MemoryExtractor:
    def __init__(self , api_key: str = None):
        self.client = Groq(api_key = api_key or os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"
        self.embedding_model = TextEmbedding()

    def extract(self , conversation_input: ConversationInput) -> ExtractionResult:
        extraction_prompt = self._build_extraction_prompt(conversation_input)
        system_prompt = """You are a memory extraction agent. Your job is to identify discrete REASONING ARTIFACTS from conversations.

Extract ONLY these types:
1. DECISION - A choice that was made ("We decided to use PostgreSQL")
2. FACT - Stable information ("The API rate limit is 100/min")
3. CONSTRAINT - A requirement or limitation ("Must support mobile devices")
4. QUESTION - An unanswered question ("How should we handle auth?")
5. ASSUMPTION - Something assumed to be true ("Users will have stable internet")

DO NOT extract:
- Greetings or social content
- Vague statements
- General conversation flow

For each artifact, provide:
- type: one of [decision, fact, constraint, question, assumption]
- content: clear, standalone description
- scope: session (temporary), project (this project), global (always true)
- confidence: 0.0 to 1.0 (how certain is this?)

Output ONLY valid JSON array of objects. No markdown, no preamble.

Example output:
[
  {
    "type": "decision",
    "content": "Using FastAPI for the backend framework",
    "scope": "project",
    "confidence": 0.9
  },
  {
    "type": "constraint",
    "content": "Response time must be under 200ms",
    "scope": "project",
    "confidence": 0.8
  }
]"""
        try:
            response = self.client.chat.completions.create(
                model = self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": extraction_prompt
                    }
                ],
                temperature=0.2,
                max_tokens=3000
            )
            content = response.choices[0].message.content
            memory_units = self._parse_extraction_response(
                content,
                conversation_input.session_id
            )
            return ExtractionResult(
                memory_units=memory_units,
                extraction_metadata={
                    "model":self.model,
                    "tokens_used":response.usage.total_tokens
                }
            )
        except Exception as e:
            return ExtractionResult(
                memory_units=[],
                extraction_metadata={"error":str(e)}
            )
        
    def _build_extraction_prompt(self, conv_input: ConversationInput) -> str:
        context=""
        if conv_input.conversation_history:
            history_text = "\n".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in conv_input.conversation_history[-5:]  # Last 5 messages
            ])
            context = f"Recent conversation:\n{history_text}\n\n"
        
        return f"""{context}Current message: {conv_input.user_message}
Extract memory artifacts from this conversation. Return ONLY a JSON array."""
    
    def _parse_extraction_response(
        self,
        llm_response:str,
        session_id:str
    ) -> List[MemoryUnit]:
        try:
            json_start = llm_response.find('[')
            json_end = llm_response.find(']') + 1

            if json_start == -1 or json_end ==0:
                return[]

            json_str = llm_response[json_start:json_end]
            artifacts = json.loads(json_str)

            memory_units = []
            for artifact in artifacts:
                try:
                    memory_unit = MemoryUnit(
                        type = MemoryType(artifact['type']),
                        content = artifact['content'],
                        scope = MemoryScope(artifact['scope']),
                        confidence=float(artifact.get('confidence',0.7)),
                        lifecycle=MemoryLifecycle.ACTIVE,
                        source_session=session_id
                    )
                    memory_units.append(memory_unit)
                except (KeyError , ValueError) as e:
                    continue
            return memory_units
        except json.JSONDecodeError:
            return []
    
    def generate_embedding(self,text:str) -> List[float]:
        embeddings = list(self.embedding_model.embed([text]))
        embedding = embeddings[0]
        # embedding = self.embedding_model.encode(
        #     text,
        #     normalize_embeddings=True
        # )
        return embedding.tolist()

