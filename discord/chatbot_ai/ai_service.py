import os
import asyncio
import aiohttp
import json
import time
from typing import List, Dict, Optional, Tuple
from django.utils import timezone
from datetime import datetime, timedelta
from asgiref.sync import sync_to_async
from .models import ChatbotSession, ChatbotMessage, ChatbotConfiguration, ChatbotTraining

class AIService:
    """Servicio para interactuar con APIs de IA"""
    
    def __init__(self):
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        self.gemini_api_key = os.environ.get('GEMINI_API_KEY')
        self.default_provider = os.environ.get('AI_PROVIDER', 'openai')
        self.max_retries = 3
        self.timeout = 30
    
    async def get_system_prompt(self) -> str:
        """Obtiene el prompt del sistema desde la base de datos"""
        try:
            # Obtener prompt del sistema
            system_prompt = await self._get_config_value('system_prompt', self._get_default_system_prompt())
            
            # Obtener entrenamientos activos
            trainings = await self._get_active_trainings()
            
            # Construir prompt completo
            full_prompt = system_prompt
            
            if trainings:
                full_prompt += "\n\n## Información Adicional:\n"
                for training in trainings:
                    full_prompt += f"\n### {training['name']}\n{training['content']}\n"
            
            return full_prompt
            
        except Exception as e:
            print(f"Error obteniendo system prompt: {e}")
            return self._get_default_system_prompt()
    
    def _get_default_system_prompt(self) -> str:
        """Prompt por defecto del sistema"""
        return """Eres un asistente de IA especializado en odontología y la comunidad IMAX. 

CARACTERÍSTICAS:
- Eres experto en odontología, tratamientos, procedimientos y mejores prácticas
- Respondes de manera profesional pero amigable
- Mantienes un tono educativo y constructivo
- Siempre recomiendas consultar con profesionales cuando sea necesario
- Respetas las reglas de la comunidad IMAX

REGLAS IMPORTANTES:
1. NUNCA proporciones diagnósticos médicos específicos
2. Siempre recomienda consultar con un dentista profesional para casos específicos
3. Mantén las conversaciones educativas y constructivas
4. Respeta los diferentes niveles de conocimiento de los usuarios
5. Si no estás seguro de algo, dilo claramente

RESPUESTAS:
- Sé conciso pero completo
- Usa emojis moderadamente
- Incluye referencias cuando sea apropiado
- Mantén un tono profesional pero accesible"""

    async def _get_config_value(self, name: str, default: str | None = None) -> str:
        """Obtiene un valor de configuración"""
        try:
            from invitation_roles.models import BotConfiguration
            config = await sync_to_async(
                lambda: BotConfiguration.objects.filter(name=name, is_active=True).first()
            )()
            return config.value if config else (default or "")
        except Exception:
            return default or ""
    
    async def _get_api_key_from_config(self, provider: str) -> str:
        """Obtiene la API key desde la configuración de la base de datos"""
        try:
            from invitation_roles.models import BotConfiguration
            config_name = f"{provider}_api_key"
            config = await sync_to_async(
                lambda: BotConfiguration.objects.filter(name=config_name, is_active=True).first()
            )()
            return config.value if config else ""
        except Exception:
            return ""
    
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
        session: ChatbotSession,
        provider: str | None = None
    ) -> Tuple[str, int, float]:
        """
        Genera respuesta de la IA
        
        Returns:
            Tuple[str, int, float]: (respuesta, tokens_usados, tiempo_procesamiento)
        """
        start_time = time.time()
        
        try:
            # Obtener prompt del sistema y contexto
            system_prompt = await self.get_system_prompt()
            context_messages = await self.get_context_messages(session)
            
            # Construir mensajes para la API
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(context_messages)
            messages.append({"role": "user", "content": user_message})
            
            # Elegir proveedor
            provider = provider or await self._get_config_value('ai_provider', 'openai')
            
            if provider == 'openai':
                response, tokens = await self._call_openai(messages)
            elif provider == 'gemini':
                response, tokens = await self._call_gemini(messages)
            else:
                raise ValueError(f"Proveedor no soportado: {provider}. Use 'openai' o 'gemini'")
            
            processing_time = time.time() - start_time
            
            return response, tokens, processing_time
            
        except Exception as e:
            print(f"Error generando respuesta: {e}")
            processing_time = time.time() - start_time
            return f"Lo siento, ocurrió un error al procesar tu mensaje. Por favor, inténtalo de nuevo. (Error: {str(e)[:100]})", 0, processing_time
    
    async def _call_openai(self, messages: List[Dict]) -> Tuple[str, int]:
        """Llama a la API de OpenAI"""
        api_key = self.openai_api_key or await self._get_api_key_from_config('openai')
        if not api_key:
            raise ValueError("OpenAI API key no configurada")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4",
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7,
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
        
        # Esto nunca debería ejecutarse, pero satisface el type checker
        raise Exception("Error inesperado en OpenAI API")
    
    async def _call_gemini(self, messages: List[Dict]) -> Tuple[str, int]:
        """Llama a la API de Google Gemini"""
        api_key = self.gemini_api_key or await self._get_api_key_from_config('gemini')
        if not api_key:
            raise ValueError("Gemini API key no configurada")
        
        model_name = await self._get_config_value('gemini_model', 'gemini-2.5-flash')
        api_version = await self._get_config_value('gemini_api_version', 'v1')
        print(f"🔍 Usando modelo Gemini: {model_name} (API: {api_version})")
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Convertir formato de mensajes para Gemini
        system_prompt = messages[0]['content'] if messages[0]['role'] == 'system' else ""
        conversation_messages = messages[1:] if messages[0]['role'] == 'system' else messages
        
        # Construir contenido para Gemini
        contents = []
        if system_prompt:
            contents.append({
                "parts": [{"text": system_prompt}],
                "role": "user"
            })
            contents.append({
                "parts": [{"text": "Entendido, actuaré como un asistente especializado en odontología."}],
                "role": "model"
            })
        
        for msg in conversation_messages:
            contents.append({
                "parts": [{"text": msg['content']}],
                "role": "user" if msg['role'] == 'user' else "model"
            })
        
        data = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1000,
                "topP": 0.8,
                "topK": 10
            }
        }
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(self.max_retries):
                try:
                    url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model_name}:generateContent?key={api_key}"
                    async with session.post(
                        url,
                        headers=headers,
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            content = result['candidates'][0]['content']['parts'][0]['text']
                            tokens = len(content.split()) * 1.3
                            return content, int(tokens)
                        else:
                            error_text = await response.text()
                            raise Exception(f"Gemini API error {response.status}: {error_text}")
                
                except asyncio.TimeoutError:
                    if attempt == self.max_retries - 1:
                        raise Exception("Timeout en Gemini API")
                    await asyncio.sleep(2 ** attempt)
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise e
                    await asyncio.sleep(2 ** attempt)
        
        raise Exception("Error inesperado en Gemini API")

# Instancia global del servicio
ai_service = AIService()
