import os
import aiohttp
import asyncio
from typing import List, Dict, Tuple
from asgiref.sync import sync_to_async
from pgvector.django import CosineDistance


class VectorService:
    """Servicio para embeddings y búsqueda vectorial"""
    
    def __init__(self):
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dimensions = 1536
        self.timeout = 30
    
    def _get_api_key(self) -> str:
        """Obtiene la API key de OpenAI desde variables de entorno"""
        api_key = os.environ.get('OPENAI_API_KEY', '')
        if not api_key:
            raise ValueError("OPENAI_API_KEY no configurada en variables de entorno")
        return api_key
    
    async def create_embedding(self, text: str) -> List[float]:
        """Crea un embedding para un texto usando OpenAI"""
        api_key = self._get_api_key()
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.embedding_model,
            "input": text,
            "encoding_format": "float"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['data'][0]['embedding']
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenAI Embeddings API error {response.status}: {error_text}")
    
    async def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Crea embeddings para múltiples textos en batch"""
        api_key = self._get_api_key()
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.embedding_model,
            "input": texts,
            "encoding_format": "float"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    sorted_data = sorted(result['data'], key=lambda x: x['index'])
                    return [item['embedding'] for item in sorted_data]
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenAI Embeddings API error {response.status}: {error_text}")
    
    async def search_similar_chunks(
        self, 
        query: str, 
        limit: int = 5,
        course_filter: str | None = None
    ) -> List[Dict]:
        """Busca los chunks más similares a una consulta"""
        from .models import ChatbotKnowledgeChunk
        
        query_embedding = await self.create_embedding(query)
        
        def search_db():
            queryset = ChatbotKnowledgeChunk.objects.all()
            
            if course_filter:
                queryset = queryset.filter(course=course_filter)
            
            results = queryset.annotate(
                distance=CosineDistance('embedding', query_embedding)
            ).order_by('distance')[:limit]
            
            return [
                {
                    'content': chunk.content,
                    'source_file': chunk.source_file,
                    'course': chunk.get_course_display(),
                    'module': chunk.module,
                    'distance': chunk.distance,
                    'similarity': 1 - chunk.distance
                }
                for chunk in results
            ]
        
        return await sync_to_async(search_db)()
    
    def format_context_for_llm(self, chunks: List[Dict]) -> str:
        """Formatea los chunks encontrados como contexto para el LLM"""
        if not chunks:
            return ""
        
        context_parts = ["## Información Relevante de IMAX:\n"]
        
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"### Fuente {i}: {chunk['course']} - {chunk['module']}\n"
                f"{chunk['content']}\n"
            )
        
        return "\n".join(context_parts)


vector_service = VectorService()

