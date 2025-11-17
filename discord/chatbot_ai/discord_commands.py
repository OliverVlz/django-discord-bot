import discord
import asyncio
from discord.ext import commands
from asgiref.sync import sync_to_async
from .chatbot_service import chatbot_service
from .models import ChatbotSession, ChatbotRole, ChatbotTraining

class ChatbotCog(commands.Cog):
    """Comandos del chatbot de IA"""
    
    def __init__(self, bot):
        self.bot = bot
        self.chatbot_service = chatbot_service
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Envía mensaje fijo cuando el bot está listo"""
        await self._send_pinned_message_if_needed()
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Escucha mensajes en canales de chatbot"""
        # Ignorar mensajes del bot
        if message.author.bot:
            return
        
        # Verificar si es un canal de chatbot
        if not await self._is_chatbot_channel(message.channel):
            return
        
        # Ignorar comandos (empiezan con !)
        if message.content.startswith('!'):
            return
        
        # Procesar mensaje del chatbot
        await self._process_chatbot_message(message)
    
    async def _is_chatbot_channel(self, channel) -> bool:
        """Verifica si el canal es un canal de chatbot"""
        try:
            # Solo verificar configuración del canal específico
            chatbot_channel_id = await self._get_bot_config('chatbot_channel_id')
            return bool(chatbot_channel_id and str(channel.id) == str(chatbot_channel_id))
            
        except Exception:
            return False
    
    async def _process_chatbot_message(self, message):
        """Procesa un mensaje del chatbot"""
        try:
            user_id = str(message.author.id)
            username = message.author.display_name
            channel_id = str(message.channel.id)
            
            # Obtener rol del usuario
            user_role_id = await self._get_user_role_id(message.author)
            if not user_role_id:
                await message.reply("❌ No se pudo determinar tu rol. Contacta a un administrador.")
                return
            
            # Verificar permisos
            can_use, error_msg = await self.chatbot_service.can_user_use_chatbot(user_id, user_role_id)
            if not can_use:
                await message.reply(error_msg)
                return
            
            # Mostrar que está procesando
            processing_msg = await message.reply("🤖 Procesando tu mensaje...")
            
            # Crear o obtener sesión
            session = await self.chatbot_service.create_or_get_session(
                user_id, username, channel_id, user_role_id
            )
            
            # Procesar mensaje
            ai_response, success = await self.chatbot_service.process_message(
                session, message.content, str(message.id)
            )
            
            # Actualizar mensaje con respuesta
            embed = discord.Embed(
                title="🤖 Asistente IA",
                description=ai_response,
                color=0x00ff00 if success else 0xff0000
            )
            
            embed.set_footer(
                text=f"Respondiendo a {username}",
                icon_url=message.author.avatar.url if message.author.avatar else None
            )
            
            await processing_msg.edit(content=None, embed=embed)
            
            # Agregar reacciones para feedback
            if success:
                await message.add_reaction("✅")
            else:
                await message.add_reaction("❌")
            
            # Enviar mensaje de bienvenida si es la primera vez del usuario en este canal
            await self._send_welcome_message_if_needed(message, session)
            
        except Exception as e:
            print(f"Error procesando mensaje del chatbot: {e}")
            try:
                await message.reply("❌ Error procesando tu mensaje. Por favor, inténtalo de nuevo.")
            except:
                pass
    
    async def _send_welcome_message_if_needed(self, message, session):
        """Envía mensaje de bienvenida si es la primera vez del usuario en este canal"""
        try:
            # Verificar si es la primera vez del usuario en este canal
            from .models import ChatbotMessage
            existing_messages = await sync_to_async(
                lambda: ChatbotMessage.objects.filter(session__user_id=session.user_id, session__channel_id=session.channel_id).count()
            )()
            
            # Si es el primer mensaje del usuario en este canal, enviar bienvenida
            if existing_messages == 1:  # El mensaje actual cuenta como 1
                welcome_embed = discord.Embed(
                    title="👋 ¡Bienvenido al Chatbot IA!",
                    description="**Especializado en Odontología y Comunidad IMAX**",
                    color=0x00ff00
                )
                
                welcome_embed.add_field(
                    name="📝 Uso Rápido",
                    value="**Solo escribe tu pregunta** y el bot responderá automáticamente.\n\n**Ejemplos:**\n• \"¿Cómo hago una restauración?\"\n• \"¿Qué composite recomiendas?\"\n• \"¿Técnicas de endodoncia?\"",
                    inline=False
                )
                
                welcome_embed.add_field(
                    name="🎭 Límites por Rol",
                    value="• **VIP**: 50 mensajes/día\n• **Premium**: 30 mensajes/día\n• **Básico**: 10 mensajes/día\n\nUsa `!ai_stats` para ver tu uso",
                    inline=False
                )
                
                welcome_embed.add_field(
                    name="⚠️ Recordatorio",
                    value="• No reemplaza consulta profesional\n• Siempre consulta con tu dentista\n• Respeta las reglas del servidor",
                    inline=False
                )
                
                welcome_embed.set_footer(text="💡 Comando: !ai_help para ayuda completa")
                
                # Enviar mensaje de bienvenida (se auto-elimina en 30 segundos)
                welcome_msg = await message.channel.send(embed=welcome_embed)
                
                # Auto-eliminar después de 30 segundos
                await asyncio.sleep(30)
                try:
                    await welcome_msg.delete()
                except:
                    pass  # Ignorar si no se puede eliminar
                    
        except Exception as e:
            print(f"Error enviando mensaje de bienvenida: {e}")
            # No es crítico, continuar sin error
    
    async def _send_pinned_message_if_needed(self):
        """Envía mensaje fijo en el canal del chatbot si no existe uno"""
        try:
            # Obtener ID del canal del chatbot
            chatbot_channel_id = await self._get_bot_config('chatbot_channel_id')
            if not chatbot_channel_id:
                return  # No hay canal configurado
            
            # Obtener el canal
            channel = self.bot.get_channel(int(chatbot_channel_id))
            if not channel:
                print(f"Canal del chatbot no encontrado: {chatbot_channel_id}")
                return
            
            # Verificar si ya hay mensajes fijos del bot
            pinned_messages = await channel.pins()
            bot_pinned_exists = any(
                msg.author.id == self.bot.user.id and 
                "Chatbot IA - Información" in msg.embeds[0].title if msg.embeds else False
                for msg in pinned_messages
            )
            
            if bot_pinned_exists:
                return  # Ya existe mensaje fijo del bot
            
            # Crear embed de información
            info_embed = discord.Embed(
                title="🤖 Chatbot IA - Información",
                description="**Especializado en Odontología y Comunidad IMAX**",
                color=0x00ff00
            )
            
            info_embed.add_field(
                name="📝 Uso Rápido",
                value="**Solo escribe tu pregunta** y el bot responderá automáticamente.\n\n**Ejemplos:**\n• \"¿Cómo hago una restauración?\"\n• \"¿Qué composite recomiendas?\"\n• \"¿Técnicas de endodoncia?\"",
                inline=False
            )
            
            info_embed.add_field(
                name="🎭 Límites por Rol",
                value="• **VIP**: 50 mensajes/día\n• **Premium**: 30 mensajes/día\n• **Básico**: 10 mensajes/día\n\nUsa `!ai_stats` para ver tu uso",
                inline=False
            )
            
            info_embed.add_field(
                name="⚡ Comandos Disponibles",
                value="• `!ai_info` - Información básica\n• `!ai_help` - Ayuda completa\n• `!ai_stats` - Estadísticas de uso",
                inline=False
            )
            
            info_embed.add_field(
                name="⚠️ Recordatorio",
                value="• No reemplaza consulta profesional\n• Siempre consulta con tu dentista\n• Respeta las reglas del servidor",
                inline=False
            )
            
            info_embed.set_footer(text="💡 Para ayuda completa usa: !ai_help")
            
            # Enviar mensaje y fijarlo
            pinned_msg = await channel.send(embed=info_embed)
            await pinned_msg.pin()
            
            print(f"✅ Mensaje fijo enviado en canal del chatbot: {channel.name}")
            
        except Exception as e:
            print(f"Error enviando mensaje fijo automático: {e}")
            # No es crítico, continuar sin error
    
    async def _get_user_role_id(self, member) -> str:
        """Obtiene el ID del rol más alto del usuario"""
        try:
            # Obtener roles del usuario ordenados por posición (más alto primero)
            user_roles = sorted(member.roles, key=lambda r: r.position, reverse=True)
            
            # Buscar el primer rol que esté configurado en el chatbot
            for role in user_roles:
                chatbot_role = await sync_to_async(
                    lambda: ChatbotRole.objects.filter(role_id=str(role.id), is_active=True).first()
                )()
                if chatbot_role:
                    return str(role.id)
            
            # Si no tiene rol configurado, usar el rol por defecto
            default_role_id = await self._get_bot_config('default_chatbot_role_id')
            return default_role_id or ""
            
        except Exception as e:
            print(f"Error obteniendo rol del usuario: {e}")
            return ""
    
    async def _get_bot_config(self, name: str, default: str | None = None) -> str:
        """Obtiene configuración del bot"""
        try:
            from invitation_roles.models import BotConfiguration
            config = await sync_to_async(
                lambda: BotConfiguration.objects.filter(name=name, is_active=True).first()
            )()
            return config.value if config else (default or "")
        except Exception:
            return default or ""
    
    @commands.command(name='ai_stats')
    async def ai_stats(self, ctx):
        """Muestra estadísticas de uso del chatbot"""
        try:
            user_id = str(ctx.author.id)
            stats = await self.chatbot_service.get_usage_stats(user_id)
            
            if "error" in stats:
                await ctx.reply(f"❌ {stats['error']}")
                return
            
            embed = discord.Embed(
                title="📊 Estadísticas del Chatbot IA",
                color=0x00ff00
            )
            
            embed.add_field(
                name="🎭 Rol",
                value=stats['role_name'],
                inline=True
            )
            
            embed.add_field(
                name="📅 Uso Diario",
                value=f"{stats['daily_used']}/{stats['daily_limit']}",
                inline=True
            )
            
            embed.add_field(
                name="📆 Uso Mensual",
                value=f"{stats['monthly_used']}/{stats['monthly_limit']}",
                inline=True
            )
            
            embed.add_field(
                name="⏳ Restante Hoy",
                value=f"{stats['remaining_daily']} mensajes",
                inline=True
            )
            
            embed.add_field(
                name="📊 Restante Mes",
                value=f"{stats['remaining_monthly']} mensajes",
                inline=True
            )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            print(f"Error en comando ai_stats: {e}")
            await ctx.reply("❌ Error obteniendo estadísticas")
    
    @commands.command(name='ai_help')
    async def ai_help(self, ctx):
        """Muestra ayuda del chatbot"""
        embed = discord.Embed(
            title="🤖 Ayuda del Chatbot IA",
            description="Sistema de asistencia inteligente especializado en odontología",
            color=0x00ff00
        )
        
        embed.add_field(
            name="💬 Cómo usar",
            value="Simplemente escribe tu pregunta en este canal y el bot responderá automáticamente.",
            inline=False
        )
        
        embed.add_field(
            name="🎯 Especialidades",
            value="• Odontología general\n• Procedimientos dentales\n• Mejores prácticas\n• Materiales dentales\n• Técnicas clínicas",
            inline=False
        )
        
        embed.add_field(
            name="⚡ Comandos",
            value="`!ai_stats` - Ver estadísticas de uso\n`!ai_help` - Mostrar esta ayuda",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Importante",
            value="• No reemplaza la consulta profesional\n• Siempre consulta con tu dentista\n• Respeta las reglas de la comunidad",
            inline=False
        )
        
        await ctx.reply(embed=embed)
    
    @commands.command(name='ai_info')
    async def ai_info(self, ctx):
        """Muestra información básica del chatbot"""
        embed = discord.Embed(
            title="🤖 Chatbot IA - Información",
            description="**Especializado en Odontología y Comunidad IMAX**",
            color=0x00ff00
        )
        
        embed.add_field(
            name="📝 Uso Rápido",
            value="**Solo escribe tu pregunta** y el bot responderá automáticamente.\n\n**Ejemplos:**\n• \"¿Cómo hago una restauración?\"\n• \"¿Qué composite recomiendas?\"\n• \"¿Técnicas de endodoncia?\"",
            inline=False
        )
        
        embed.add_field(
            name="🎭 Límites por Rol",
            value="• **VIP**: 50 mensajes/día\n• **Premium**: 30 mensajes/día\n• **Básico**: 10 mensajes/día\n\nUsa `!ai_stats` para ver tu uso",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Recordatorio",
            value="• No reemplaza consulta profesional\n• Siempre consulta con tu dentista\n• Respeta las reglas del servidor",
            inline=False
        )
        
        embed.set_footer(text="💡 Comando: !ai_help para ayuda completa")
        
        await ctx.reply(embed=embed)
    
    @commands.command(name='ai_pin')
    @commands.has_permissions(administrator=True)
    async def ai_pin(self, ctx):
        """Envía y fija un mensaje de información del chatbot (solo admins)"""
        try:
            # Crear embed de información
            info_embed = discord.Embed(
                title="🤖 Chatbot IA - Información",
                description="**Especializado en Odontología y Comunidad IMAX**",
                color=0x00ff00
            )
            
            info_embed.add_field(
                name="📝 Uso Rápido",
                value="**Solo escribe tu pregunta** y el bot responderá automáticamente.\n\n**Ejemplos:**\n• \"¿Cómo hago una restauración?\"\n• \"¿Qué composite recomiendas?\"\n• \"¿Técnicas de endodoncia?\"",
                inline=False
            )
            
            info_embed.add_field(
                name="🎭 Límites por Rol",
                value="• **VIP**: 50 mensajes/día\n• **Premium**: 30 mensajes/día\n• **Básico**: 10 mensajes/día\n\nUsa `!ai_stats` para ver tu uso",
                inline=False
            )
            
            info_embed.add_field(
                name="⚡ Comandos Disponibles",
                value="• `!ai_info` - Información básica\n• `!ai_help` - Ayuda completa\n• `!ai_stats` - Estadísticas de uso",
                inline=False
            )
            
            info_embed.add_field(
                name="⚠️ Recordatorio",
                value="• No reemplaza consulta profesional\n• Siempre consulta con tu dentista\n• Respeta las reglas del servidor",
                inline=False
            )
            
            info_embed.set_footer(text="💡 Para ayuda completa usa: !ai_help")
            
            # Enviar mensaje y fijarlo
            pinned_msg = await ctx.send(embed=info_embed)
            await pinned_msg.pin()
            
            await ctx.reply("✅ Mensaje de información enviado y fijado correctamente")
            
        except Exception as e:
            print(f"Error enviando mensaje fijo: {e}")
            await ctx.reply("❌ Error enviando mensaje fijo")

    @commands.command(name='ai_cleanup')
    @commands.has_permissions(administrator=True)
    async def ai_cleanup(self, ctx):
        """Limpia sesiones expiradas del chatbot (solo admins)"""
        try:
            await self.chatbot_service.cleanup_expired_sessions()
            await ctx.reply("✅ Sesiones expiradas limpiadas correctamente")
        except Exception as e:
            print(f"Error en limpieza: {e}")
            await ctx.reply("❌ Error durante la limpieza")
    
    @commands.command(name='ai_roles')
    @commands.has_permissions(administrator=True)
    async def ai_roles(self, ctx):
        """Muestra roles configurados para el chatbot (solo admins)"""
        try:
            roles = await sync_to_async(list)(
                ChatbotRole.objects.filter(is_active=True).order_by('-priority')
            )
            
            if not roles:
                await ctx.reply("❌ No hay roles configurados para el chatbot")
                return
            
            embed = discord.Embed(
                title="🎭 Roles del Chatbot IA",
                color=0x00ff00
            )
            
            for role in roles:
                embed.add_field(
                    name=f"🎭 {role.role_name}",
                    value=f"• Diario: {role.daily_limit}\n• Mensual: {role.monthly_limit}\n• Contexto: {role.max_context_messages}",
                    inline=True
                )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            print(f"Error mostrando roles: {e}")
            await ctx.reply("❌ Error obteniendo roles")

async def setup(bot):
    """Configura el cog del chatbot"""
    await bot.add_cog(ChatbotCog(bot))
