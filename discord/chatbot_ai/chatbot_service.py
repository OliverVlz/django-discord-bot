import asyncio
from typing import Optional, Tuple, List
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async
from .models import (
    ChatbotSession, ChatbotMessage, ChatbotRole, 
    ChatbotUsage, ChatbotConfiguration
)
from .ai_service import ai_service

class ChatbotService:
    """Servicio principal del chatbot"""
    
    def __init__(self):
        self.ai_service = ai_service
    
    async def can_user_use_chatbot(self, user_id: str, role_id: str) -> Tuple[bool, str]:
        """
        Verifica si un usuario puede usar el chatbot
        
        Returns:
            Tuple[bool, str]: (puede_usar, mensaje_error)
        """
        try:
            # Verificar si el rol tiene acceso
            chatbot_role = await self._get_chatbot_role(role_id)
            if not chatbot_role:
                return False, "❌ Tu rol no tiene acceso al chatbot de IA"
            
            # Verificar límites diarios y mensuales
            usage = await self._get_user_usage(user_id)
            today = timezone.now().date()
            
            daily_count = usage.daily_count if usage.date == today else 0
            is_same_month = usage.date.year == today.year and usage.date.month == today.month
            monthly_count = usage.monthly_count if is_same_month else 0
            
            if daily_count >= chatbot_role.daily_limit:
                return False, f"❌ Has alcanzado tu límite diario de {chatbot_role.daily_limit} mensajes"
            
            if monthly_count >= chatbot_role.monthly_limit:
                return False, f"❌ Has alcanzado tu límite mensual de {chatbot_role.monthly_limit} mensajes"
            
            return True, "✅ Puedes usar el chatbot"
            
        except Exception as e:
            print(f"Error verificando acceso al chatbot: {e}")
            return False, "❌ Error verificando permisos"
    
    async def create_or_get_session(self, user_id: str, username: str, channel_id: str, role_id: str) -> ChatbotSession:
        """Crea o obtiene una sesión activa del chatbot"""
        try:
            # Buscar sesión activa existente
            session = await sync_to_async(
                lambda: ChatbotSession.objects.filter(
                    user_id=user_id,
                    channel_id=channel_id,
                    is_active=True
                ).first()
            )()
            
            if session and not session.is_expired():
                # Actualizar última actividad
                session.last_activity = timezone.now()
                await sync_to_async(session.save)()
                return session
            
            # Crear nueva sesión
            session = await sync_to_async(
                ChatbotSession.objects.create
            )(
                user_id=user_id,
                username=username,
                channel_id=channel_id,
                role_id=role_id,
                expires_at=timezone.now() + timedelta(hours=24)
            )
            
            print(f"✅ Nueva sesión de chatbot creada para {username}")
            return session
            
        except Exception as e:
            print(f"Error creando sesión: {e}")
            raise
    
    async def process_message(
        self, 
        session: ChatbotSession, 
        user_message: str, 
        message_id: str
    ) -> Tuple[str, bool]:
        """
        Procesa un mensaje del usuario
        
        Returns:
            Tuple[str, bool]: (respuesta_ai, éxito)
        """
        try:
            # Generar respuesta con IA
            ai_response, tokens_used, processing_time = await self.ai_service.generate_response(
                user_message, session
            )
            
            # Guardar mensaje en la base de datos
            await self._save_message(session, message_id, user_message, ai_response, tokens_used, processing_time)
            
            # Actualizar contadores de uso
            await self._update_usage_counters(session.user_id)
            
            return ai_response, True
            
        except Exception as e:
            print(f"Error procesando mensaje: {e}")
            error_msg = f"Lo siento, ocurrió un error al procesar tu mensaje. Por favor, inténtalo de nuevo."
            return error_msg, False
    
    async def get_usage_stats(self, user_id: str) -> dict:
        """Obtiene estadísticas de uso del usuario"""
        try:
            usage = await self._get_user_usage(user_id)
            chatbot_role = await self._get_chatbot_role_by_user_id(user_id)
            
            if not chatbot_role:
                return {"error": "Rol no encontrado"}
            
            today = timezone.now().date()
            daily_used = usage.daily_count if usage.date == today else 0
            is_same_month = usage.date.year == today.year and usage.date.month == today.month
            monthly_used = usage.monthly_count if is_same_month else 0
            
            return {
                "daily_used": daily_used,
                "daily_limit": chatbot_role.daily_limit,
                "monthly_used": monthly_used,
                "monthly_limit": chatbot_role.monthly_limit,
                "remaining_daily": max(0, chatbot_role.daily_limit - daily_used),
                "remaining_monthly": max(0, chatbot_role.monthly_limit - monthly_used),
                "role_name": chatbot_role.role_name
            }
            
        except Exception as e:
            print(f"Error obteniendo estadísticas: {e}")
            return {"error": "Error obteniendo estadísticas"}
    
    async def cleanup_expired_sessions(self):
        """Limpia sesiones expiradas"""
        try:
            count = await sync_to_async(
                lambda: ChatbotSession.objects.filter(
                    expires_at__lt=timezone.now(),
                    is_active=True
                ).update(is_active=False)
            )()
            
            if count > 0:
                print(f"🧹 Limpiadas {count} sesiones expiradas")
                
        except Exception as e:
            print(f"Error limpiando sesiones: {e}")
    
    async def _get_chatbot_role(self, role_id: str) -> Optional[ChatbotRole]:
        """Obtiene configuración de rol para chatbot"""
        try:
            return await sync_to_async(
                lambda: ChatbotRole.objects.filter(role_id=role_id, is_active=True).first()
            )()
        except Exception:
            return None
    
    async def _get_chatbot_role_by_user_id(self, user_id: str) -> Optional[ChatbotRole]:
        """Obtiene configuración de rol por user_id"""
        try:
            # Buscar la sesión más reciente del usuario para obtener su rol
            session = await sync_to_async(
                lambda: ChatbotSession.objects.filter(user_id=user_id).order_by('-created_at').first()
            )()
            if session:
                return await self._get_chatbot_role(session.role_id)
            return None
        except Exception:
            return None
    
    async def _get_user_usage(self, user_id: str) -> ChatbotUsage:
        """Obtiene o crea registro de uso del usuario"""
        try:
            today = timezone.now().date()
            from .models import ChatbotUsage as UsageModel
            
            def get_or_create_usage():
                return UsageModel.objects.get_or_create(
                    user_id=user_id,
                    date=today,
                    defaults={
                        'role_id': '',
                        'daily_count': 0,
                        'monthly_count': 0
                    }
                )
            
            usage, created = await sync_to_async(get_or_create_usage)()
            return usage
        except Exception as e:
            print(f"Error obteniendo uso del usuario: {e}")
            from .models import ChatbotUsage
            return ChatbotUsage(
                user_id=user_id,
                date=timezone.now().date(),
                daily_count=0,
                monthly_count=0
            )
    
    async def _save_message(
        self, 
        session: ChatbotSession, 
        message_id: str, 
        user_message: str, 
        ai_response: str, 
        tokens_used: int, 
        processing_time: float
    ):
        """Guarda mensaje en la base de datos"""
        try:
            await sync_to_async(
                ChatbotMessage.objects.create
            )(
                session=session,
                message_id=message_id,
                user_message=user_message,
                ai_response=ai_response,
                tokens_used=tokens_used,
                processing_time=processing_time
            )
        except Exception as e:
            print(f"Error guardando mensaje: {e}")
    
    async def _update_usage_counters(self, user_id: str):
        """Actualiza contadores de uso del usuario"""
        try:
            today = timezone.now().date()
            from .models import ChatbotUsage as UsageModel
            
            def update_counters():
                with transaction.atomic():
                    usage, created = UsageModel.objects.get_or_create(
                        user_id=user_id,
                        date=today,
                        defaults={'daily_count': 0, 'monthly_count': 0}
                    )
                    
                    usage.daily_count += 1
                    
                    is_same_month = usage.date.year == today.year and usage.date.month == today.month
                    if is_same_month:
                        usage.monthly_count += 1
                    else:
                        usage.monthly_count = 1
                    
                    usage.save()
            
            await sync_to_async(update_counters)()
                
        except Exception as e:
            print(f"Error actualizando contadores: {e}")

# Instancia global del servicio
chatbot_service = ChatbotService()



