import os
import asyncio
import aiohttp
import time
from typing import List, Dict, Tuple
from asgiref.sync import sync_to_async
from .models import ChatbotSession, ChatbotMessage, ChatbotConfiguration, ChatbotTraining
from .vector_service import vector_service


class AIService:
    """Servicio para interactuar con OpenAI"""
    
    def __init__(self):
        self.max_retries = 3
        self.timeout = 30
    
    def _get_api_key(self) -> str:
        """Obtiene la API key de OpenAI desde variables de entorno"""
        api_key = os.environ.get('OPENAI_API_KEY', '')
        if not api_key:
            raise ValueError("OPENAI_API_KEY no configurada en variables de entorno (.env)")
        return api_key
    
    async def get_system_prompt(self, user_query: str | None = None) -> str:
        """Obtiene el prompt del sistema con contexto RAG relevante"""
        try:
            base_prompt = await self._get_config_value('system_prompt', self._get_default_system_prompt())
            
            trainings = await self._get_active_trainings()
            
            rag_context = ""
            if user_query:
                try:
                    rag_context = await self._get_rag_context(user_query)
                    if rag_context:
                        print(f"✅ RAG: Contexto encontrado ({len(rag_context)} caracteres)")
                    else:
                        print("⚠️ RAG: No se encontró contexto relevante")
                except Exception as e:
                    print(f"❌ Error obteniendo contexto RAG: {e}")
            
            if rag_context:
                full_prompt = f"""{rag_context}

---

## INSTRUCCIONES CRÍTICAS:

La información anterior proviene DIRECTAMENTE de los cursos oficiales IMAX (Launch y Pro). 
DEBES usar esta información como BASE PRINCIPAL y ÚNICA para responder. 

REGLAS:
1. Si el contexto IMAX menciona algo específico (ej: "no antiagregado ni anticoagulado"), DEBES incluirlo
2. NO uses conocimiento general si el contexto IMAX ya lo cubre
3. Menciona que la información proviene de IMAX cuando sea relevante
4. El contexto IMAX tiene PRIORIDAD ABSOLUTA sobre cualquier otro conocimiento

{base_prompt}"""
            else:
                full_prompt = base_prompt
            
            if trainings:
                full_prompt += "\n\n## Reglas Adicionales:\n"
                for training in trainings:
                    full_prompt += f"\n### {training['name']}\n{training['content']}\n"
            
            return full_prompt
            
        except Exception as e:
            print(f"Error obteniendo system prompt: {e}")
            return self._get_default_system_prompt()
    
    async def _get_rag_context(self, query: str, limit: int = 5) -> str:
        """Obtiene contexto relevante usando búsqueda vectorial RAG"""
        try:
            chunks = await vector_service.search_similar_chunks(query, limit=limit)
            
            if not chunks:
                return ""
            
            return vector_service.format_context_for_llm(chunks)
            
        except Exception as e:
            print(f"Error en búsqueda RAG: {e}")
            return ""
    
    def _get_default_system_prompt(self) -> str:
        """Prompt por defecto del sistema"""
        return """Eres un asistente de IA especializado en odontología y la comunidad IMAX.

Responde a las preguntas basándote ÚNICAMENTE en el contexto proporcionado cuando esté disponible.
Si hay contexto de IMAX, úsalo como base principal para tu respuesta.
Sé profesional, educativo y amigable. Siempre recomienda consultar con profesionales para casos específicos."""

    async def _get_config_value(self, name: str, default: str | None = None) -> str:
        """Obtiene un valor de configuración desde ChatbotConfiguration"""
        try:
            config = await sync_to_async(
                lambda: ChatbotConfiguration.objects.filter(name=name, is_active=True).first()
            )()
            if config:
                return config.value
            from invitation_roles.models import BotConfiguration
            bot_config = await sync_to_async(
                lambda: BotConfiguration.objects.filter(name=name, is_active=True).first()
            )()
            return bot_config.value if bot_config else (default or "")
        except Exception:
            return default or ""
    
    async def _get_active_trainings(self) -> List[Dict]:
        """Obtiene entrenamientos activos"""
        try:
            trainings = await sync_to_async(list)(
                ChatbotTraining.objects.filter(is_active=True).order_by('-priority')
            )
            return [
                {
                    'name': t.name,
                    'type': t.training_type,
                    'content': t.content,
                    'priority': t.priority
                }
                for t in trainings
            ]
        except Exception as e:
            print(f"Error obteniendo entrenamientos: {e}")
            return []
    
    async def get_context_messages(self, session: ChatbotSession, limit: int = 20) -> List[Dict]:
        """Obtiene mensajes de contexto para la conversación"""
        try:
            messages = await sync_to_async(list)(
                ChatbotMessage.objects.filter(
                    session=session
                ).order_by('-created_at')[:limit]
            )
            
            context = []
            for msg in reversed(messages):
                context.extend([
                    {"role": "user", "content": msg.user_message},
                    {"role": "assistant", "content": msg.ai_response}
                ])
            
            return context
            
        except Exception as e:
            print(f"Error obteniendo contexto: {e}")
            return []
    
    async def generate_response(
        self, 
        user_message: str, 
        session: ChatbotSession
    ) -> Tuple[str, int, float]:
        """
        Genera respuesta de la IA usando OpenAI
        
        Returns:
            Tuple[str, int, float]: (respuesta, tokens_usados, tiempo_procesamiento)
        """
        start_time = time.time()
        
        try:
            base_system_prompt = await self._get_config_value('system_prompt', self._get_default_system_prompt())
            trainings = await self._get_active_trainings()
            
            rag_context = ""
            if user_message:
                try:
                    rag_context = await self._get_rag_context(user_message)
                    if rag_context:
                        print(f"✅ RAG: Contexto encontrado ({len(rag_context)} caracteres)")
                    else:
                        print("⚠️ RAG: No se encontró contexto relevante")
                except Exception as e:
                    print(f"❌ Error obteniendo contexto RAG: {e}")
            
            system_content = base_system_prompt
            if trainings:
                system_content += "\n\n## Reglas Adicionales:\n"
                for training in trainings:
                    system_content += f"\n### {training['name']}\n{training['content']}\n"
            
            context_messages = await self.get_context_messages(session)
            print(f"📝 Contexto: {len(context_messages)} mensajes previos en historial")
            
            messages = [{"role": "system", "content": system_content}]
            messages.extend(context_messages)
            
            if rag_context:
                user_content = f"Contexto:\n{rag_context}\n\nPregunta: {user_message}"
            else:
                user_content = user_message
            
            messages.append({"role": "user", "content": user_content})
            
            response, tokens = await self._call_openai(messages)
            
            processing_time = time.time() - start_time
            
            return response, tokens, processing_time
            
        except Exception as e:
            print(f"Error generando respuesta: {e}")
            processing_time = time.time() - start_time
            return f"Lo siento, ocurrió un error al procesar tu mensaje. Por favor, inténtalo de nuevo. (Error: {str(e)[:100]})", 0, processing_time
    
    async def _call_openai(self, messages: List[Dict]) -> Tuple[str, int]:
        """Llama a la API de OpenAI"""
        api_key = self._get_api_key()
        
        model_name = await self._get_config_value('openai_model', 'gpt-4o-mini')
        print(f"🔍 Usando modelo OpenAI: {model_name}")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model_name,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.3,
            "stream": False
        }
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(self.max_retries):
                try:
                    async with session.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            content = result['choices'][0]['message']['content']
                            tokens = result['usage']['total_tokens']
                            return content, tokens
                        else:
                            error_text = await response.text()
                            raise Exception(f"OpenAI API error {response.status}: {error_text}")
                
                except asyncio.TimeoutError:
                    if attempt == self.max_retries - 1:
                        raise Exception("Timeout en OpenAI API")
                    await asyncio.sleep(2 ** attempt)
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise e
                    await asyncio.sleep(2 ** attempt)
        
        raise Exception("Error inesperado en OpenAI API")


ai_service = AIService()
