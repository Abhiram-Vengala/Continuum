from typing import List , Dict 
from src.Schemas import ( MemoryUnit , ContextState , LLMProvider , RenderRequest , RenderResult )

class ContextComposer:
    def compose(
        self,
        session_id:str ,
        user_message:str,
        working_memories:List[MemoryUnit],
        episodic_memories:List[MemoryUnit],
        semantic_memories:List[MemoryUnit]
    ) -> ContextState:
        return ContextState(
            session_id= session_id,
            working_memory=working_memories,
            episodic_memory=episodic_memories,
            semantic_memory=semantic_memories,
            user_message=user_message,
            metadata={
                "total_memories":(
                    len(working_memories)+
                    len(episodic_memories)+
                    len(semantic_memories)
                ),
                "memory_breakdown":{
                    "working":len(working_memories),
                    "episodic":len(episodic_memories),
                    "semantic":len(semantic_memories)
                }
            }
        )
    
class ProviderRenderer:
    def render(self,request: RenderRequest) -> RenderRequest:
        renderer_map = {
            LLMProvider.CHATGPT:self._render_chatgpt,
            LLMProvider.CLAUDE:self._render_claude,
            LLMProvider.GEMINI:self._render_gemini,
            LLMProvider.GROQ:self._render_groq,
        }

        renderer = renderer_map.get(request.provider,self._render_generic)
        return renderer(request.context_state,request.model)
    
    def _render_groq(self,context:ContextState,model:str=None ) -> RenderResult:
        system_parts = [
            "You are an AI assistant with access to structured memory.",
            "",
            "# ACTIVE CONTEXT",
        ]

        if context.semantic_memory:
            system_parts.append("\n## Established Knowledge:")
            for mem in context.semantic_memory:
                system_parts.append(
                    f"- [{mem.type.upper()}] {mem.content} "
                    f"(confidence: {mem.confidence:.2f})"
                )
        if context.episodic_memory:
            system_parts.append("\n## Recent Decisions:")
            for mem in context.episodic_memory[-5:]:  # Last 5
                system_parts.append(f"- {mem.content}")
        if context.working_memory:
            system_parts.append("\n## Current Session Context:")
            for mem in context.working_memory:
                system_parts.append(f"- {mem.content}")
        
        system_parts.append("\nUse this context to inform your response.")
        system_prompt = "\n".join(system_parts)

        return RenderResult(
            provider=LLMProvider.GROQ,
            system_prompt=system_prompt,
            user_prompt=context.user_message,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context.user_message}
            ],
            metadata={
                "model": model or "llama-3.3-70b-versatile"
            }
        )
    def _render_claude(
        self,
        context: ContextState,
        model: str = None
    ) -> RenderResult:
        
        system_parts = [
            "You have access to structured memory across sessions.",
            "",
            "<memory_context>"
        ]
        
        if context.semantic_memory:
            system_parts.append("\n<semantic_knowledge>")
            for mem in context.semantic_memory:
                system_parts.append(
                    f"<{mem.type}>{mem.content}</{mem.type}>"
                )
            system_parts.append("</semantic_knowledge>")
        
        if context.episodic_memory:
            system_parts.append("\n<decision_history>")
            for mem in context.episodic_memory[-5:]:
                system_parts.append(f"<event>{mem.content}</event>")
            system_parts.append("</decision_history>")
        
        if context.working_memory:
            system_parts.append("\n<active_session>")
            for mem in context.working_memory:
                system_parts.append(f"<context>{mem.content}</context>")
            system_parts.append("</active_session>")
        
        system_parts.append("</memory_context>")
        
        system_prompt = "\n".join(system_parts)
        
        return RenderResult(
            provider=LLMProvider.CLAUDE,
            system_prompt=system_prompt,
            user_prompt=context.user_message,
            messages=[
                {"role": "user", "content": context.user_message}
            ],
            metadata={
                "model": model or "claude-3-5-sonnet-20241022",
                "system": system_prompt
            }
        )
    
    def _render_chatgpt(
        self,
        context: ContextState,
        model: str = None
    ) -> RenderResult:
        system_parts = [
            "You are an AI assistant with persistent memory across conversations.",
            ""
        ]
        
        if context.semantic_memory:
            system_parts.append("Relevant knowledge:")
            for mem in context.semantic_memory:
                system_parts.append(f"• {mem.content}")
            system_parts.append("")
        
        if context.episodic_memory:
            system_parts.append("Recent activity:")
            for mem in context.episodic_memory[-3:]:
                system_parts.append(f"• {mem.content}")
            system_parts.append("")
        
        if context.working_memory:
            system_parts.append("Current context:")
            for mem in context.working_memory:
                system_parts.append(f"• {mem.content}")
        
        system_prompt = "\n".join(system_parts)
        
        return RenderResult(
            provider=LLMProvider.CHATGPT,
            system_prompt=system_prompt,
            user_prompt=context.user_message,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context.user_message}
            ],
            metadata={
                "model": model or "gpt-4-turbo-preview"
            }
        )
    
    def _render_gemini(
        self,
        context: ContextState,
        model: str = None
    ) -> RenderResult:
        
        parts = []
        
        if context.semantic_memory or context.episodic_memory:
            parts.append("Based on our previous conversations:")
            
            if context.semantic_memory:
                for mem in context.semantic_memory[:3]:
                    parts.append(f"- {mem.content}")
            
            if context.episodic_memory:
                for mem in context.episodic_memory[-2:]:
                    parts.append(f"- {mem.content}")
            
            parts.append("")
        
        parts.append(context.user_message)
        
        user_prompt = "\n".join(parts)
        
        return RenderResult(
            provider=LLMProvider.GEMINI,
            system_prompt=None,  # Gemini doesn't use system prompts
            user_prompt=user_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            metadata={
                "model": model or "gemini-pro"
            }
        )
    
    def _render_generic(
        self,
        context: ContextState,
        model: str = None
    ) -> RenderResult:
        """Generic fallback renderer"""
        return self._render_groq(context, model)