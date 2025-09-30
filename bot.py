import os
import asyncio
import threading
from datetime import datetime, timedelta
import sys # Importar sys

import django
from django.conf import settings
from django.utils import timezone

import discord
from discord.ext import commands
from discord.ui import Button, View # Importar Button y View
from asgiref.sync import sync_to_async # Importar sync_to_async

# Añadir el directorio padre del paquete Django al sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'discord')))

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'discord.discord.settings') # Corregido
django.setup()

from invitation_roles.models import Invite, AccessRole, BotConfiguration

# --- Helper Functions ---

async def get_bot_config(name, default=None):
    """
    Obtiene una configuración del bot desde la base de datos.
    Si no existe o no está activa, devuelve el valor por defecto.
    """
    try:
        config = await sync_to_async(
            lambda: BotConfiguration.objects.filter(name=name, is_active=True).first()
        )()
        return config.value if config else default
    except Exception as e:
        print(f"Error al obtener configuración '{name}': {e}")
        return default

async def get_bot_config_int(name, default=None):
    """
    Obtiene una configuración del bot como entero.
    """
    value = await get_bot_config(name, default)
    try:
        return int(value) if value else default
    except (ValueError, TypeError):
        print(f"Error al convertir configuración '{name}' a entero: {value}")
        return default

async def update_bot_config(name, value, description=None):
    """
    Actualiza o crea una configuración del bot en la base de datos.
    """
    try:
        config, created = await sync_to_async(
            lambda: BotConfiguration.objects.get_or_create(
                name=name,
                defaults={
                    'value': str(value),
                    'configuration_type': 'message' if 'message' in name else 'channel',
                    'description': description or f'Configuración para {name}',
                    'is_active': True
                }
            )
        )()
        
        if not created:
            config.value = str(value)
            if description:
                config.description = description
            await sync_to_async(config.save)()
            
        print(f"✅ Configuración {'creada' if created else 'actualizada'}: {name} = {value}")
        return True
    except Exception as e:
        print(f"Error al actualizar configuración '{name}': {e}")
        return False

class AcceptRulesView(View):
    def __init__(self):
        super().__init__(timeout=None) # Timeout=None para que la vista persista
    
    @discord.ui.button(label="Acepto las Reglas", style=discord.ButtonStyle.success, custom_id="accept_rules_button")
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        # Lógica para procesar la aceptación de reglas
        print(f"Botón 'Acepto las Reglas' presionado por {interaction.user.name}")
        
        # Diferir la respuesta inmediatamente para evitar timeouts con múltiples clics
        await interaction.response.defer(ephemeral=True)
        
        # Verificar si el usuario ya tiene el rol asignado o no hay una invitación pendiente
        try:
            invite_entry = await sync_to_async(Invite.objects.get)(
                member_id=str(interaction.user.id),
                status='PENDING_VERIFICATION'
            )
            
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("Error: No se pudo encontrar el servidor.", ephemeral=True)
                return
            
            member = guild.get_member(interaction.user.id)
            if not member:
                await interaction.followup.send("Error: No se pudo encontrar a su miembro en el servidor.", ephemeral=True)
                return
            
            role_id_str = invite_entry.role_id
            role = guild.get_role(int(role_id_str))
            
            if role:
                bot_member = guild.me
                if role.position >= bot_member.top_role.position:
                    await interaction.followup.send(f"No se pudo asignar el rol {role.name}. El rol del bot es igual o inferior al rol a asignar.", ephemeral=True)
                    return
                
                await member.add_roles(role)
                
                # Mensaje de interacción completo con toda la información
                presentation_channel_id = await get_bot_config('presentation_channel_id')
                presentation_mention = f"<#{presentation_channel_id}>" if presentation_channel_id else "canal de presentaciones"
                
                welcome_message = f"""🎉 ¡Felicidades! Has aceptado las reglas de la Comunidad IMAX y ahora tienes acceso a los canales.

¡Bienvenido oficialmente a nuestra comunidad! 🦷✨

👋 **Siguiente paso:** Te invitamos a presentarte en {presentation_mention} para que la comunidad pueda conocerte mejor."""
                
                await interaction.followup.send(welcome_message, ephemeral=True)
                print(f"Rol {role.name} asignado a {member.name} después de aceptar las reglas.")
                
                # Actualizar el estado de la invitación
                invite_entry.status = 'USED'
                invite_entry.used_at = timezone.now()
                await sync_to_async(invite_entry.save)()
                print(f"Invite para {member.name} marcado como USED después de verificación.")
            else:
                await interaction.followup.send(f"Error: El rol con ID {role_id_str} no se encontró en el servidor.", ephemeral=True)
                print(f"Rol con ID {role_id_str} no encontrado en el servidor Discord para {member.name}.")
            
        except Invite.DoesNotExist:
            # No hay invitación PENDING_VERIFICATION, verificar si ya tiene rol activo
            guild = interaction.guild
            member = guild.get_member(interaction.user.id) if guild else None
            
            if not guild or not member:
                await interaction.followup.send("Error: No se pudo verificar su estado en el servidor.", ephemeral=True)
                return
            
            try:
                # Obtener roles de acceso activos desde la base de datos
                access_roles_from_db = await sync_to_async(
                    lambda: list(AccessRole.objects.filter(is_active=True).values_list('role_id', 'name'))
                )()
                
                access_role_ids = [int(role_id) for role_id, name in access_roles_from_db if role_id.isdigit()]
                access_role_names = {int(role_id): name for role_id, name in access_roles_from_db if role_id.isdigit()}
                
                has_access_role = False
                member_access_roles = []
                all_member_roles = [f"{role.name} ({role.id})" for role in member.roles if role.name != "@everyone"]
                
                print(f"DEBUG - {interaction.user.name}: Roles de acceso activos en BD: {access_role_names}")
                print(f"DEBUG - {interaction.user.name}: Roles del usuario: {all_member_roles}")
                
                for role_id in access_role_ids:
                    role = guild.get_role(role_id)
                    if role and role in member.roles:
                        has_access_role = True
                        role_display_name = access_role_names.get(role_id, role.name)
                        member_access_roles.append(f"{role_display_name} ({role.name})")
                
                print(f"DEBUG - {interaction.user.name}: ¿Tiene rol de acceso? {has_access_role}")
                
                if has_access_role:
                    # Tiene rol de acceso → registrar en BD si no existe y confirmar acceso
                    await interaction.followup.send("Ya tienes acceso a los canales de la comunidad. Si experimentas algún problema con los permisos, comunícate con soporte.", ephemeral=True)
                    print(f"El miembro {interaction.user.name} tiene roles de acceso: {member_access_roles}. Posiblemente añadido manualmente.")
                    
                    # Opcional: Crear entrada automática en BD para usuarios sin registro
                    # (descomenta si quieres registrar automáticamente estos usuarios)
                    # try:
                    #     await sync_to_async(Invite.objects.get_or_create)(
                    #         member_id=str(interaction.user.id),
                    #         defaults={
                    #             'invite_code': 'MANUAL_ACCESS',
                    #             'role_id': str(member_access_roles[0]) if member_access_roles else '0',
                    #             'email': f'{interaction.user.name}@manual.access',
                    #             'status': 'USED',
                    #             'used_at': timezone.now(),
                    #         }
                    #     )
                    # except Exception as e:
                    #     print(f"Error al crear entrada automática para {interaction.user.name}: {e}")
                    
                else:
                    # No tiene roles de acceso → verificar invitaciones en BD
                    used_invite = await sync_to_async(
                        lambda: Invite.objects.filter(
                            member_id=str(interaction.user.id),
                            status='USED'
                        ).first()
                    )()
                    
                    if used_invite:
                        # Tiene invitación USED pero no el rol → posible problema
                        expected_role = guild.get_role(int(used_invite.role_id))
                        await interaction.followup.send("Parece que no tienes una invitación pendiente de verificación. Si eres un usuario recurrente o experimentas problemas, comunícate con soporte.", ephemeral=True)
                        print(f"El miembro {interaction.user.name} tiene invitaciones USED pero no tiene el rol correspondiente.")
                    else:
                        # No tiene invitaciones ni roles → usuario sin acceso
                        await interaction.followup.send("No se encontró una invitación pendiente de verificación para usted. Por favor, diríjase a soporte y explique lo ocurrido.", ephemeral=True)
                        print(f"No se encontró ninguna invitación para el miembro {interaction.user.name} y no tiene roles de acceso.")
                    
            except Exception as e:
                await interaction.followup.send("Ocurrió un error al verificar su estado. Por favor, comunícate con soporte.", ephemeral=True)
                print(f"Error al verificar estado de invitaciones para {interaction.user.name}: {e}")
        except Exception as e:
            await interaction.followup.send("Ocurrió un error al procesar su solicitud. Por favor, inténtelo de nuevo más tarde.", ephemeral=True)
            print(f"Error al procesar la interacción del botón de {interaction.user.name}: {e}")

# --- Lógica del Bot de Discord ---

intents = discord.Intents.default()
intents.members = True # Necesario para guildMemberAdd
intents.guilds = True
intents.invites = True

bot = commands.Bot(command_prefix='!', intents=intents)

invite_cache = {}
invite_cache_lock = threading.Lock()  # Protege el cache de condiciones de carrera
discord_api_semaphore = asyncio.Semaphore(3)  # Máximo 3 llamadas simultáneas a Discord API

@bot.event
async def on_ready():
    print(f'Bot listo como {bot.user}!')
    await populate_guild_invites()

    # Configurar el mensaje de aceptación de reglas con botón
    rule_channel_id = await get_bot_config('rules_channel_id')
    rule_message_id = await get_bot_config('rules_message_id')
    rules_text = """
## Reglas de la Comunidad IMAX :scroll:

1. **Respeto ante todo** :raised_hands:
   Nos hablamos con humildad, empatía y ganas de crecer juntos.
2. **Usa cada canal para su propósito** :open_file_folder:
   Esto mantiene el orden y ayuda a que todos encuentren lo que buscan.
3. **Nada de spam ni autopromoción** :no_entry_sign:
   No se permiten mensajes repetitivos, publicidad personal ni enlaces externos sin autorización previa.
4. **Preguntas clínicas** :tooth:
   Publícalas siempre en el canal correspondiente a tu nivel.
5. **Dudas técnicas o de soporte** :tools:
   Escríbelas en tu grupo correspondiente o en los canales de soporte designados.
6. **Niveles de aprendizaje** :chart_with_upwards_trend:
   - Puedes ver los niveles superiores para inspirarte y aprender.
   - Recuerda apoyar y orientar a los compañeros de niveles inferiores.
7. **Comunidad, no solo clases** :handshake:
   Este espacio es para compartir, ayudarnos y crecer juntos, no solo para recibir información.
8. **Cuida el espacio y a ti mismo** :seedling:
   IMAX es parte de tu proceso de transformación. Hazlo un lugar seguro y constructivo.
   
**Al hacer clic en el botón, aceptas nuestras reglas.**
    """

    if not rule_channel_id:
        print("rules_channel_id no está configurado en la base de datos. No se puede configurar el mensaje de reglas.")
        return

    try:
        rules_channel = bot.get_channel(int(rule_channel_id))
        if not rules_channel:
            print(f"Canal de reglas con ID {rule_channel_id} no encontrado.")
            return

        view = AcceptRulesView()
        rules_message = None
        
        if rule_message_id:
            try:
                rules_message = await rules_channel.fetch_message(int(rule_message_id))
                await rules_message.edit(content=rules_text, view=view)
                print(f"Mensaje de reglas actualizado en el canal {rules_channel.name}.")
            except (discord.NotFound, discord.Forbidden): # Capturar Forbidden también
                print(f"Mensaje de reglas con ID {rule_message_id} no encontrado o no se pudo editar. Enviando uno nuevo.")
                rules_message = await rules_channel.send(content=rules_text, view=view)
                await update_bot_config('rules_message_id', rules_message.id, 'ID del mensaje de reglas con el botón de aceptación')
                print(f"Nuevo mensaje de reglas enviado y configuración actualizada automáticamente: {rules_message.id}")
                
        else:
            rules_message = await rules_channel.send(content=rules_text, view=view)
            await update_bot_config('rules_message_id', rules_message.id, 'ID del mensaje de reglas con el botón de aceptación')
            print(f"Mensaje de reglas enviado por primera vez y configuración creada automáticamente: {rules_message.id}")
        
        # Verificar si el mensaje de reglas está fijado
        if rules_message:
            if rules_message.pinned:
                print(f"✅ El mensaje de reglas está fijado correctamente.")
            else:
                try:
                    await rules_message.pin()
                    print(f"📌 Mensaje de reglas fijado automáticamente.")
                except discord.Forbidden:
                    print(f"⚠️ No se pudo fijar el mensaje de reglas. El bot necesita permisos de 'Gestionar mensajes'.")
                except discord.HTTPException as e:
                    if e.code == 30003:  # Cannot execute action on this channel type
                        print(f"⚠️ No se pueden fijar mensajes en este tipo de canal.")
                    else:
                        print(f"⚠️ Error al fijar mensaje de reglas: {e}")
            
        bot.add_view(view) # Añadir la vista al bot para que persista

    except Exception as e:
        print(f"Error al configurar el mensaje de reglas: {e}")

    # Configurar mensajes fijados en canales
    await setup_presentation_channel_message()
    await setup_welcome_channel_message()

async def setup_presentation_channel_message():
    """Configura un mensaje fijado en el canal de presentaciones"""
    presentation_channel_id = await get_bot_config('presentation_channel_id')
    presentation_message_id = await get_bot_config('presentation_message_id')
    
    if not presentation_channel_id:
        print("presentation_channel_id no está configurado en la base de datos. No se puede configurar el mensaje de presentaciones.")
        return

    try:
        presentation_channel = bot.get_channel(int(presentation_channel_id))
        if not presentation_channel:
            print(f"Canal de presentaciones con ID {presentation_channel_id} no encontrado.")
            return

        presentation_text = """
🌟 **¡Bienvenido al canal de presentaciones de IMAX!** 🦷✨

Este es el primer paso real en IMAX Universe.  
Cuéntanos brevemente quién eres, desde dónde te conectas y qué esperas conseguir con tu formación en implantología.

**Puedes usar esta guía si lo necesitas:**

1. **Nombre y ciudad:**
2. **¿A qué te dedicas hoy en tu clínica?**
3. **¿Qué nivel IMAX estás cursando?**
4. **¿Qué te gustaría lograr como implantólogo?**
5. **Algo curioso o divertido sobre ti** 😄

💥 **YO TE RECOMIENDO HACERLO EN VIDEO, ES SUPER IMPORTANTE PONERNOS TODOS CARA Y EMPEZAR A EXPONERNOS.** Adelante, grábate un video de máximo 1 minuto y preséntate tal y como eres. (No tengas miedo a que nadie te juzgue o al que dirán, aquí eso no existe).

---

💥 **Este espacio no es solo para compartir... ¡es para conectar!**
Aquí es donde comienza tu red de apoyo, compañeros y crecimiento.
        """

        presentation_message = None
        
        if presentation_message_id:
            try:
                presentation_message = await presentation_channel.fetch_message(int(presentation_message_id))
                await presentation_message.edit(content=presentation_text)
                print(f"Mensaje de presentaciones actualizado en el canal {presentation_channel.name}.")
            except (discord.NotFound, discord.Forbidden):
                print(f"Mensaje de presentaciones con ID {presentation_message_id} no encontrado o no se pudo editar. Enviando uno nuevo.")
                presentation_message = await presentation_channel.send(content=presentation_text)
                await update_bot_config('presentation_message_id', presentation_message.id, 'ID del mensaje fijado en el canal de presentaciones')
                print(f"Nuevo mensaje de presentaciones enviado y configuración actualizada automáticamente: {presentation_message.id}")
        else:
            presentation_message = await presentation_channel.send(content=presentation_text)
            await update_bot_config('presentation_message_id', presentation_message.id, 'ID del mensaje fijado en el canal de presentaciones')
            print(f"Mensaje de presentaciones enviado por primera vez y configuración creada automáticamente: {presentation_message.id}")

        # Verificar si el mensaje está fijado y fijarlo si no lo está
        if presentation_message:
            if presentation_message.pinned:
                print(f"✅ El mensaje de presentaciones está fijado correctamente.")
            else:
                try:
                    await presentation_message.pin()
                    print(f"📌 Mensaje de presentaciones fijado automáticamente.")
                except discord.Forbidden:
                    print(f"⚠️ No se pudo fijar el mensaje de presentaciones. El bot necesita permisos de 'Gestionar mensajes'.")
                except discord.HTTPException as e:
                    if e.code == 30003:  # Cannot execute action on this channel type
                        print(f"⚠️ No se pueden fijar mensajes en este tipo de canal.")
                    else:
                        print(f"⚠️ Error al fijar mensaje de presentaciones: {e}")

    except Exception as e:
        print(f"Error al configurar el mensaje de presentaciones: {e}")

async def setup_welcome_channel_message():
    """Configura un mensaje fijado en el canal de bienvenida"""
    welcome_channel_id = await get_bot_config('welcome_channel_id')
    welcome_message_id = await get_bot_config('welcome_message_id')
    
    if not welcome_channel_id:
        print("welcome_channel_id no está configurado en la base de datos. No se puede configurar el mensaje de bienvenida.")
        return

    try:
        welcome_channel = bot.get_channel(int(welcome_channel_id))
        if not welcome_channel:
            print(f"Canal de bienvenida con ID {welcome_channel_id} no encontrado.")
            return

        welcome_text = """
👋 **BIENVENIDO A IMAX UNIVERSE**

Este servidor es tu centro de entrenamiento, mentalidad y comunidad para crecer como implantólogo.

🔍 **¿QUÉ DEBES HACER AHORA?**
✅ 1. Lee las y ACEPTA las 📜 reglas-del-servidor
✅ 2. Preséntate en 🙋 presentate-aquí → Queremos conocerte
✅ 3. Accede a tu nivel (Launch, Base, Starts, etc.) y participa
✅ 4. Visita los canales generales:
🔥 mentalidad-ganadora
🧘‍♂️ habitos-diarios
💼 marca-personal-imax

🎁 Si tienes bonus, ve a 🎁 bonus-y-descargables

📢 Para novedades importantes, mira siempre 📢 anuncios-generales

---

🎓 **¿A QUÉ TIENES ACCESO?**
Tu nivel actual → Participar
Niveles inferiores → Apoyar y guiar
Niveles superiores → Solo ver (modo inspiración)

👑 ¡Bienvenido al universo IMAX! Aquí empieza tu transformación.
        """

        welcome_message = None
        
        if welcome_message_id:
            try:
                welcome_message = await welcome_channel.fetch_message(int(welcome_message_id))
                await welcome_message.edit(content=welcome_text)
                print(f"Mensaje de bienvenida actualizado en el canal {welcome_channel.name}.")
            except (discord.NotFound, discord.Forbidden):
                print(f"Mensaje de bienvenida con ID {welcome_message_id} no encontrado o no se pudo editar. Enviando uno nuevo.")
                welcome_message = await welcome_channel.send(content=welcome_text)
                await update_bot_config('welcome_message_id', welcome_message.id, 'ID del mensaje fijado en el canal de bienvenida')
                print(f"Nuevo mensaje de bienvenida enviado y configuración actualizada automáticamente: {welcome_message.id}")
        else:
            welcome_message = await welcome_channel.send(content=welcome_text)
            await update_bot_config('welcome_message_id', welcome_message.id, 'ID del mensaje fijado en el canal de bienvenida')
            print(f"Mensaje de bienvenida enviado por primera vez y configuración creada automáticamente: {welcome_message.id}")

        # Verificar si el mensaje está fijado y fijarlo si no lo está
        if welcome_message:
            if welcome_message.pinned:
                print(f"✅ El mensaje de bienvenida está fijado correctamente.")
            else:
                try:
                    await welcome_message.pin()
                    print(f"📌 Mensaje de bienvenida fijado automáticamente.")
                except discord.Forbidden:
                    print(f"⚠️ No se pudo fijar el mensaje de bienvenida. El bot necesita permisos de 'Gestionar mensajes'.")
                except discord.HTTPException as e:
                    if e.code == 30003:  # Cannot execute action on this channel type
                        print(f"⚠️ No se pueden fijar mensajes en este tipo de canal.")
                    else:
                        print(f"⚠️ Error al fijar mensaje de bienvenida: {e}")

    except Exception as e:
        print(f"Error al configurar el mensaje de bienvenida: {e}")

async def populate_guild_invites():
    guild_id = await get_bot_config('guild_id')
    if not guild_id:
        print("guild_id no está configurado en la base de datos.")
        return
    
    guild = bot.get_guild(int(guild_id))
    if not guild:
        print(f"Servidor Discord con ID {guild_id} no encontrado.")
        return

    try:
        invites = await guild.invites()
        with invite_cache_lock:
            invite_cache[guild.id] = {invite.code: invite.uses for invite in invites if invite.code}
        print(f'Cache de invites para {guild.name} ({guild.id}) populado. Total: {len(invite_cache[guild.id])} invites.')
    except discord.Forbidden:
        print(f"Permisos insuficientes para obtener invites en el servidor {guild.name}.")
    except Exception as e:
        print(f"Error al poblar cache de invites para guild {guild.id}: {e}")


@bot.event
async def on_invite_create(invite):
    guild_id = invite.guild.id
    with invite_cache_lock:
        if guild_id not in invite_cache:
            invite_cache[guild_id] = {}
        invite_cache[guild_id][invite.code] = invite.uses
    print(f"Invite creado: {invite.code} para guild {guild_id}. Añadido al cache.")

@bot.event
async def on_invite_delete(invite):
    guild_id = invite.guild.id
    with invite_cache_lock:
        if guild_id in invite_cache and invite.code in invite_cache[guild_id]:
            del invite_cache[guild_id][invite.code]
    print(f"Invite borrado: {invite.code} de guild {guild_id}. Eliminado del cache.")

@bot.event
async def on_member_join(member):
    print(f"Miembro {member.name} se ha unido al servidor.")
    guild_id = member.guild.id

    # Usar semáforo para limitar llamadas simultáneas a Discord API
    async with discord_api_semaphore:
        try:
            # 1. Proteger acceso al cache con lock
            with invite_cache_lock:
                old_invites_map = invite_cache.get(guild_id, {})
                old_invite_uses = {code: uses for code, uses in old_invites_map.items()}

            # 2. Obtener los invites *actuales* de Discord *después* de la unión
            # Añadir pequeño delay para evitar rate limits
            await asyncio.sleep(0.1)
            new_invites_collection = await member.guild.invites()
            new_invite_uses = {invite.code: invite.uses for invite in new_invites_collection if invite.code}

            used_code = None
            
            # Paso A: Buscar invites que incrementaron sus usos
            for code, new_uses in new_invite_uses.items():
                old_uses = old_invite_uses.get(code, 0)
                if new_uses > old_uses:
                    used_code = code
                    print(f"Debug (on_member_join): Invite {code} aumentó usos. Antiguo: {old_uses}, Nuevo: {new_uses}")
                    break

            # Paso B: Si no se encontró en el Paso A, buscar un invite de un solo uso que fue eliminado
            if not used_code:
                for code, old_uses in old_invite_uses.items():
                    if code not in new_invite_uses:
                        used_code = code
                        print(f"Debug (on_member_join): Invite {code} estaba en el cache antiguo pero no en el nuevo (probablemente usado y eliminado).")
                        break
                        
            # Actualizar el cache GLOBAL de forma protegida
            with invite_cache_lock:
                invite_cache[guild_id] = new_invite_uses

            # Logs para depuración del estado de los invites
            print('Debug (on_member_join): Cache de Invites (antes de la unión):', old_invite_uses)
            print('Debug (on_member_join): Invites actuales (después de la unión):', new_invite_uses)
            
        except discord.Forbidden:
            print(f"Permisos insuficientes para obtener invites para {member.name}.")
            return
        except Exception as e:
            print(f"Error al procesar invites para {member.name}: {e}")
            return

    if not used_code:
        print(f"Miembro {member.name} se unió sin un código rastreable (URL vanity / re-unión). A revisar: Cache, permisos del bot, o si es un re-unión/URL vanity.")
        return

    print(f"Miembro {member.name} se unió usando el invite: {used_code}")

    # Verificar en la base de datos de Django
    try:
        # Envolver operaciones de DB en sync_to_async
        invite_entry = await sync_to_async(Invite.objects.get)(invite_code=used_code)
        
        # Actualizar la entrada de la invitación para marcarla como pendiente de verificación
        invite_entry.status = 'PENDING_VERIFICATION'
        invite_entry.member_id = str(member.id)
        invite_entry.rule_message_id = await get_bot_config('rules_message_id')
        invite_entry.rule_channel_id = await get_bot_config('rules_channel_id')
        await sync_to_async(invite_entry.save)()
        print(f"Invite {used_code} marcado como PENDING_VERIFICATION para miembro {member.name}.")
        
        # Enviar mensaje de bienvenida personalizado en el canal de bienvenida
        welcome_channel_id = await get_bot_config('welcome_channel_id')
        if welcome_channel_id:
            try:
                welcome_channel = bot.get_channel(int(welcome_channel_id))
                if welcome_channel:
                    rules_channel_id = await get_bot_config('rules_channel_id')
                    rules_mention = f"<#{rules_channel_id}>" if rules_channel_id else "canal de reglas"
                    welcome_message = await welcome_channel.send(f"🎉 ¡Bienvenido {member.mention} a la Comunidad IMAX! Para acceder a todos los canales, por favor dirígete a {rules_mention} y haz clic en el botón **'Acepto las Reglas'**.")
                    
                    # Eliminar el mensaje después de 30 segundos para mantenerlo "privado"
                    async def delete_after_delay():
                        await asyncio.sleep(90)
                        try:
                            await welcome_message.delete()
                        except:
                            pass  # Ignorar si no se puede eliminar
                    
                    asyncio.create_task(delete_after_delay())
                else:
                    print(f"Canal de bienvenida con ID {welcome_channel_id} no encontrado.")
            except Exception as e:
                print(f"Error al enviar mensaje de bienvenida: {e}")
        else:
            print("welcome_channel_id no está configurado en la base de datos.")

    except Invite.DoesNotExist:
        print(f"Invite {used_code} no encontrado en la base de datos de Django.")
    except Exception as e:
        print(f"Error al procesar la unión de miembro para {member.name} con invite {used_code}: {e}")


discord_bot_token = os.environ.get('DISCORD_BOT_TOKEN')
if not discord_bot_token:
    print("DISCORD_BOT_TOKEN no está configurado en las variables de entorno.")
else:
    bot.run(discord_bot_token)
