from typing import List , Optional , Dict
from datetime import datetime , timezone
import re

from src.Schemas import (
    MemoryUnit , MemoryType , MemoryScope , MemoryLifecycle,
    PolicyDecision , PolicyRule
)

class MemoryPolicyEngine:
    def __init__(self):
        self.rules: List[PolicyRule] = self._initialize_default_rules()
    
    def _initialize_default_rules(self) -> List[PolicyRule]:
        return [
            PolicyRule(
                name = "High_confidence_decisions",
                condition="Decision with confidence > 0.8",
                action = "Store in semantic memory",
                priority=10
            ),
            PolicyRule(
                name="project_constraints",
                condition="Constraint with project/global scope",
                action="Store in semantic memory",
                priority=8
            ),
            PolicyRule(
                name="decision_events",
                condition="Any decision type",
                action="Store in episodic memory",
                priority=7
            ),
            PolicyRule(
                name="low_confidence_questions",
                condition="Question with confidence < 0.5",
                action="Do not store",
                priority=3
            ),
        ]
    
    def evaluate(
        self,
        memory_unit:MemoryUnit,
        existing_memories:List[MemoryUnit],
    ) -> PolicyDecision:
        if (memory_unit.type == MemoryType.DECISION and 
            memory_unit.confidence > 0.8):
            return PolicyDecision(
                should_store=True,
                target_store="semantic",
                reason="High confidence decision - stable knowledge"
            )
        if(memory_unit.type == MemoryType.CONSTRAINT and 
           memory_unit.scope in [MemoryScope.PROJECT , MemoryScope.GLOBAL] ):
            return PolicyDecision(
                should_store = True,
                target_store="semantic",
                reason="Project constraint - long-term applicable"
            )
        if(memory_unit.type == MemoryType.FACT and
           memory_unit.scope == MemoryScope.SESSION):
            return PolicyDecision(
                should_store=True,
                target_store="working",
                reason="Session fact - temporary relevance"
            )
        if memory_unit.type == MemoryType.DECISION :
            deprecate_ids = self._check_contradictions(memory_unit, existing_memories)
            return PolicyDecision(
                should_store=True,
                target_store="episodic",
                deprecate_existing=deprecate_ids,
                reason="Decision event - append to episodic log"
            )
        if (memory_unit.type == MemoryType.QUESTION and
            memory_unit.confidence < 0.5):
            return PolicyDecision(
                should_store=False,
                target_store=None,
                reason="Low confidence question - not worth storing"
            )
        
        # Rule: High confidence facts → semantic memory
        if (memory_unit.type == MemoryType.FACT and
            memory_unit.confidence > 0.7):
            return PolicyDecision(
                should_store=True,
                target_store="semantic",
                reason="High confidence fact - stable knowledge"
            )
        
        return PolicyDecision(
            should_store=True,
            target_store="working",
            reason="Default - working memory with TTL"
        )
    
    def _check_contradictions(
        self,
        new_memory:MemoryUnit,
        existing_memories:List[MemoryUnit]
    ) -> List[str]:
        deprecate_ids = []
        for existing in existing_memories:
            if(existing.type != new_memory.type or
               existing.scope != new_memory.scope):
                continue
            if self._semantic_overlap(new_memory.content , existing.content) >0.7:
                if new_memory.confidence > existing.confidence:
                    deprecate_ids.append(existing.id)
        return deprecate_ids
    
    def _semantic_overlap(self,content1:str , content2:str) -> float:
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1&words2
        union = words1 | words2
        return len(intersection) / len(union) if union else 0.0
    
    def evaluate_batch(
        self,
        memory_units: List[MemoryUnit],
        existing_memories: List[MemoryUnit]
    ) -> List[PolicyDecision]:
        return[
            self.evaluate(unit, existing_memories) for unit in memory_units
        ]
    
    def should_summarize_working_memory(
        self,
        working_memory_count:int,
        token_threshold: int = 2000
    ) -> bool : 
        estimated_tokens = working_memory_count * 100
        return estimated_tokens > token_threshold
    
    def get_ttl_for_scope(self,scope:MemoryScope) -> int:
        ttl_map = {
            MemoryScope.SESSION:3600,
            MemoryScope.PROJECT:86400,
            MemoryScope.GLOBAL:604800,
        }
        return ttl_map.get(scope,3600)
    