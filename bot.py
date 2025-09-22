import os
from datetime import datetime, timedelta
import sys # Importar sys

import django
from django.conf import settings
from django.utils import timezone

import discord
from discord.ext import commands
from asgiref.sync import sync_to_async # Importar sync_to_async

# Añadir el directorio padre del paquete Django al sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'discord')))

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'discord.discord.settings') # Corregido
django.setup()

from invitation_roles.models import Invite

# --- Lógica del Bot de Discord ---

intents = discord.Intents.default()
intents.members = True # Necesario para guildMemberAdd
intents.guilds = True
intents.invites = True

bot = commands.Bot(command_prefix='!', intents=intents)

invite_cache = {}

@bot.event
async def on_ready():
    print(f'Bot listo como {bot.user}!')
    await populate_guild_invites()

async def populate_guild_invites():
    guild_id = os.environ.get('GUILD_ID')
    if not guild_id:
        print("GUILD_ID no está configurado en las variables de entorno.")
        return
    
    guild = bot.get_guild(int(guild_id))
    if not guild:
        print(f"Servidor Discord con ID {guild_id} no encontrado.")
        return

    try:
        invites = await guild.invites()
        invite_cache[guild.id] = {invite.code: invite.uses for invite in invites if invite.code}
        print(f'Cache de invites para {guild.name} ({guild.id}) populado. Total: {len(invite_cache[guild.id])} invites.')
    except discord.Forbidden:
        print(f"Permisos insuficientes para obtener invites en el servidor {guild.name}.")
    except Exception as e:
        print(f"Error al poblar cache de invites para guild {guild.id}: {e}")


@bot.event
async def on_invite_create(invite):
    guild_id = invite.guild.id
    if guild_id not in invite_cache:
        invite_cache[guild_id] = {}
    invite_cache[guild_id][invite.code] = invite.uses
    print(f"Invite creado: {invite.code} para guild {guild_id}. Añadido al cache.")

@bot.event
async def on_invite_delete(invite):
    guild_id = invite.guild.id
    if guild_id in invite_cache and invite.code in invite_cache[guild_id]:
        del invite_cache[guild_id][invite.code]
        print(f"Invite borrado: {invite.code} de guild {guild_id}. Eliminado del cache.")

@bot.event
async def on_member_join(member):
    print(f"Miembro {member.name} se ha unido al servidor.")
    guild_id = member.guild.id

    # 1. Obtener el estado del cache de invites *antes* de la unión del miembro.
    old_invites_map = invite_cache.get(guild_id, {})
    old_invite_uses = {code: uses for code, uses in old_invites_map.items()}

    # 2. Obtener los invites *actuales* de Discord *después* de la unión
    new_invites_collection = await member.guild.invites()
    new_invite_uses = {invite.code: invite.uses for invite in new_invites_collection if invite.code}

    used_code = None
    
    # Paso A: Buscar invites que incrementaron sus usos (para multi-uso o single-uso no eliminados aún)
    for code, new_uses in new_invite_uses.items():
        old_uses = old_invite_uses.get(code, 0)
        if new_uses > old_uses:
            used_code = code
            print(f"Debug (on_member_join): Invite {code} aumentó usos. Antiguo: {old_uses}, Nuevo: {new_uses}")
            break

    # Paso B: Si no se encontró en el Paso A, buscar un invite de un solo uso que fue eliminado
    if not used_code:
        for code, old_uses in old_invite_uses.items():
            # Si un invite estaba en nuestro cache antiguo pero ya no está en la colección recién fetched,
            # significa que probablemente fue un invite de un solo uso que fue consumido y eliminado.
            if code not in new_invite_uses:
                used_code = code
                print(f"Debug (on_member_join): Invite {code} estaba en el cache antiguo pero no en el nuevo (probablemente usado y eliminado).")
                break
            
    # Actualizar el cache GLOBAL con el nuevo estado de los invites para este guild *después* de la detección
    invite_cache[guild_id] = new_invite_uses

    # Logs para depuración del estado de los invites (opcional, pero útil)
    print('Debug (on_member_join): Cache de Invites (antes de la unión):', old_invite_uses)
    print('Debug (on_member_join): Invites actuales (después de la unión):', new_invite_uses)

    if not used_code:
        print(f"Miembro {member.name} se unió sin un código rastreable (URL vanity / re-unión). A revisar: Cache, permisos del bot, o si es un re-unión/URL vanity.")
        return

    print(f"Miembro {member.name} se unió usando el invite: {used_code}")

    # Verificar en la base de datos de Django
    try:
        # Envolver operaciones de DB en sync_to_async
        invite_entry = await sync_to_async(Invite.objects.get)(invite_code=used_code, status='PENDING')
        
        # Asignar rol
        role_id_str = invite_entry.role_id
        guild = member.guild
        role = guild.get_role(int(role_id_str))

        if role:
            # Asegurarse de que el rol del bot sea más alto que el rol a asignar
            bot_member = member.guild.me # 'member.guild.me' es el miembro del bot en el guild
            if role.position >= bot_member.top_role.position: # Corregido: usar .top_role.position
                print(f"No se pudo asignar rol {role.name} a {member.name}. El rol del bot es igual o inferior.")
                return

            await member.add_roles(role)
            print(f"Rol {role.name} asignado a {member.name}.")

            # Envolver operaciones de DB en sync_to_async
            invite_entry.status = 'USED'
            invite_entry.used_at = timezone.now()
            invite_entry.member_id = str(member.id)
            await sync_to_async(invite_entry.save)()
            print(f"Invite {used_code} marcado como USED y miembro ID {member.id} guardado.")
        else:
            print(f"Rol con ID {role_id_str} no encontrado en el servidor Discord.")

    except Invite.DoesNotExist:
        print(f"Invite {used_code} no encontrado o no pendiente en la base de datos de Django.")
    except Exception as e:
        print(f"Error al procesar la unión de miembro para {member.name} con invite {used_code}: {e}")


discord_bot_token = os.environ.get('DISCORD_BOT_TOKEN')
if not discord_bot_token:
    print("DISCORD_BOT_TOKEN no está configurado en las variables de entorno.")
else:
    bot.run(discord_bot_token)
