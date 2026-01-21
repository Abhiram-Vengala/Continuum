from typing import Optional , List , Dict
from datetime import datetime , timezone , timedelta
from collections import defaultdict
from contextlib import contextmanager
import numpy as np
import sqlite3
import json
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance , VectorParams , PointStruct,
    Filter , FieldCondition , MatchValue , Range
)


from src.Schemas import(
    MemoryUnit , MemoryScope , MemoryType , MemoryLifecycle,
    WorkingMemoryEntry , EpisodicMemoryEntry , SemanticMemoryEntry
)
import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"


class WorkingMemoryStore:
    def __init__(self):
        self._store: Dict[str,WorkingMemoryEntry] = {}
    
    def add(self , memory_unit: MemoryUnit , ttl_seconds: int = 3600):
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        entry = WorkingMemoryEntry(
            memory_unit=memory_unit,
            ttl_seconds=ttl_seconds,
            expires_at = expires_at
        )
        self._store[memory_unit.id] = entry
    
    def get_active(self, session_id: str) -> List[MemoryUnit]:
        now = datetime.now(timezone.utc)
        active = []

        for entry in self._store.values():
            if(entry.memory_unit.source_session == session_id and 
               entry.expires_at > now and
               entry.memory_unit.lifecycle == MemoryLifecycle.ACTIVE ):
                active.append(entry.memory_unit)
            
        return active
    
    def cleanup_expired(self):
        now = datetime.now(timezone.utc)
        expired_ids = [
            uid for uid, entry in self._store.items()
            if entry.expires_at <= now
        ]
        for uid in expired_ids:
            del self._store[uid]
        
    def get_by_id(self, memory_id: str) -> Optional[MemoryUnit]:
        entry = self._store.get(memory_id)
        return entry.memory_unit if entry else None
    
class EpisodicMemoryStore :
    def __init__(self, db_path:str = "episodic_memory.db"):
        self.db_path = db_path
        self._initialize_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _initialize_db(self):
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodic_events(
                    sequence_number INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    lifecycle TEXT NOT NULL,
                    source_session TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    metadata TEXT
                )
"""
            )
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_id 
                ON episodic_events(id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session 
                ON episodic_events(source_session)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created 
                ON episodic_events(created_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sequence 
                ON episodic_events(sequence_number)
            """)
    
    def add(self , memory_unit: MemoryUnit , event_type:str = "decision"):
        with self._get_connection() as conn :
            conn.execute(
                """
                INSERT INTO episodic_events(
                    id , event_type , memory_type , content , scope ,
                    confidence , lifecycle , source_session ,
                    created_at , updated_at , metadata
                ) VALUES(? , ? , ? , ? , ? , ? , ? , ? , ? , ? , ?)
            """ , (
                memory_unit.id ,
                event_type,
                memory_unit.type,
                memory_unit.content ,
                memory_unit.scope,
                memory_unit.confidence , 
                memory_unit.lifecycle ,
                memory_unit.source_session ,
                memory_unit.created_at.isoformat(),
                memory_unit.updated_at.isoformat(),
                json.dumps(memory_unit.metadata)
            )
            )
    
    def get_session_timeline(self, session_id:str) -> List[MemoryUnit]:
        with self._get_connection() as conn :
            cursor = conn.execute(
                """
                SELECT * FROM episodic_events 
                WHERE source_session = ?
                ORDER BY sequence_number ASC
            """,(session_id,)
            )
            return [self._row_to_memory_unit(row) for row in cursor.fetchall()]
    
    def get_recent(self , limit :int = 10) -> List[MemoryUnit]:
        with self._get_connection() as conn :
            cursor = conn.execute(
                """
                SELECT * FROM episodic_events 
                ORDER BY sequence_number DESC 
                LIMIT ?
            """ , (limit,)
            )
            return [self._row_to_memory_unit(row) for row in cursor.fetchall()]
    
    def get_by_type(self , event_type: str , limit: int = 50) -> List[MemoryUnit]:
        with self._get_connection() as conn :
            cursor = conn.execute(
                """
                SELECT * FROM episodic_events
                WHERE event_type = ?
                ORDER BY sequence_number DESC
                LIMIT ?
            """ , (event_type , limit)
            )
            return [self._row_to_memory_unit(row) for row in cursor.fetchall()]
    
    def get_by_date_range(self , start_date:datetime , end_date:datetime) -> List[MemoryUnit]:
        with  self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM episodic_events
                WHERE  created_at BETWEEN ? AND ?
                ORDER BY sequence_number ASC 
            """ , (start_date.isoformat() , end_date.isoformat())
            )
            return [self._row_to_memory_unit(row) for row in cursor.fetchall()]
    
    def _row_to_memory_unit(self, row: sqlite3.Row)-> MemoryUnit:
        return MemoryUnit(
            id=row['id'],
            type=MemoryType(row['memory_type']),
            content=row['content'],
            scope=MemoryScope(row['scope']),
            confidence=row['confidence'],
            lifecycle=MemoryLifecycle(row['lifecycle']),
            source_session=row['source_session'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )

class SemanticMemoryStore:
    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        collection_name: str = "semantic_memory",
        vector_size: int = 384
    ):
        # self.client = QdrantClient(host=qdrant_host,port=qdrant_port)
        self.client = QdrantClient(":memory:")
        self.collection_name = collection_name
        self.vector_size = vector_size
        self._initialize_collection()
    
    def _initialize_collection(self):
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size = self.vector_size,
                    distance=Distance.COSINE
                )
            )
    
    def add(self,memory_unit:MemoryUnit, embedding:List[float]):
        # Fixed: removed .value calls since enums are already strings
        payload = {
            "id":memory_unit.id,
            "type":memory_unit.type,  # Already a string
            "content":memory_unit.content,
            "scope":memory_unit.scope,  # Already a string
            "confidence":memory_unit.confidence,
            "lifecycle": memory_unit.lifecycle,  # Already a string
            "source_session":memory_unit.source_session,
            "created_at": memory_unit.created_at.isoformat(),
            "updated_at": memory_unit.updated_at.isoformat(),
            "retrieval_count": 0,
            "metadata": memory_unit.metadata
        }

        point = PointStruct(
            id = memory_unit.id,
            vector=embedding,
            payload=payload
        )
        self.client.upsert(
            collection_name=self.collection_name,
            points = [point]
        )
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10 ,
        scope_filter: Optional[List[MemoryScope]] = None ,
        type_filter: Optional[List[MemoryScope]] = None ,
        min_confidence: float = 0.5
    ) -> List[MemoryUnit]:
        must_conditions = []
        must_conditions.append(
            FieldCondition(
                key ="lifecycle",
                match=MatchValue(value = MemoryLifecycle.ACTIVE.value)
            )
        )
        must_conditions.append(
            FieldCondition(
                key="confidence",
                range=Range(gte=min_confidence)
            )
        )
        if scope_filter:
            must_conditions.append(
                FieldCondition(
                    key="scope",
                    match=MatchValue(
                        any=[scope.value for scope in scope_filter]
                    )
                )
            )
        if type_filter:
            must_conditions.append(
                FieldCondition(
                    key="type",
                    match=MatchValue(
                        any = [mem_type.value for mem_type in type_filter]
                    )
                )
            )
        query_filter = Filter(must=must_conditions) if must_conditions else None
        
        # Use query() instead of search() for compatibility with different qdrant-client versions
        try:
            search_result = self.client.query_points(
                collection_name = self.collection_name,
                query = query_embedding,
                query_filter=query_filter,
                limit=top_k
            ).points
        except AttributeError:
            # Fallback for older versions
            search_result = self.client.search(
                collection_name = self.collection_name,
                query_vector = query_embedding,
                query_filter=query_filter,
                limit=top_k
            )
        
        memories = []
        for hit in search_result:
            memory = self._payload_to_memory_unit(hit.payload)
            memories.append(memory)
            self._update_retrieval_stats(hit.id)
        return memories
    
    def get_by_scope(self,scope: MemoryScope) -> List[MemoryUnit]:
        search_result = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="scope",
                        match=MatchValue(value=scope.value)
                    ),
                    FieldCondition(
                        key="lifecycle",
                        match=MatchValue(value=MemoryLifecycle.ACTIVE.value)
                    )
                ]
            ),
            limit=1000
        )
        return [self._payload_to_memory_unit(point.payload) for  point in search_result[0]]
    
    def deprecate(self,memory_id: str):
        self.client.set_payload(
            collection_name=self.collection_name,
            payload = {
                "lifecycle":MemoryLifecycle.DEPRECATED.value,
                "updated_at":datetime.now(timezone.utc).isoformat()
            },
            points = [memory_id]
        )
    
    def reinforce(self,memory_id: str,confidence_boost:float=0.1):
        points = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[memory_id]
        )
        if points:
            current_confidence = points[0].payload.get('confidence',0.7)
            new_confidence = min(1.0 , current_confidence +confidence_boost)
            self.client.set_payload(
                collection_name=self.collection_name,
                payload={
                    "confidence": new_confidence,
                    "lifecycle":MemoryLifecycle.REINFORCED.value,
                    "updated_at":datetime.now(timezone.utc).isoformat()
                },
                points=[memory_id]
            )
    
    def _update_retrieval_stats(self,memory_id:str):
        points = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[memory_id]
        )
        if points:
            current_count = points[0].payload.get('retrieval_count',0)
            self.client.set_payload(
                collection_name=self.collection_name,
                payload={
                    "retrieval_count":current_count + 1,
                    "last_retrieved":datetime.now(timezone.utc).isoformat()
                },
                points=[memory_id]
            )
    
    def _payload_to_memory_unit(self,payload:Dict) -> MemoryUnit:
        return MemoryUnit(
            id=payload['id'],
            type=MemoryType(payload['type']),
            content=payload['content'],
            scope=MemoryScope(payload['scope']),
            confidence=payload['confidence'],
            lifecycle=MemoryLifecycle.ACTIVE,
            source_session=payload['source_session'],
            created_at=datetime.fromisoformat(payload['created_at']),
            updated_at=datetime.fromisoformat(payload['updated_at']),
            metadata=payload.get('metadata',{})
        )

class MemoryStoreManager:
        def __init__(
            self,
            sqlite_db_path:str = "episodic_memory.db",
            qdrant_host : str = "localhost",
            qdrant_port : int = 6333,
            qdrant_collection : str = "semantic_memory",
            vector_size : int = 384
        ):
            self.working = WorkingMemoryStore()
            self.episodic = EpisodicMemoryStore(db_path=sqlite_db_path)
            self.semantic = SemanticMemoryStore(
                qdrant_host=qdrant_host,
                qdrant_port=qdrant_port,
                collection_name=qdrant_collection,
                vector_size=vector_size
            )
        
        def get_all_memories(self , session_id:str) -> List[MemoryUnit]:
            all_memories = []
            all_memories.extend(self.working.get_active(session_id))
            all_memories.extend(self.episodic.get_session_timeline(session_id))
            all_memories.extend(self.semantic.get_by_scope(MemoryScope.SESSION))
            return all_memories