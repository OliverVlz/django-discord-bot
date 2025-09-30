from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Invite, BotConfiguration
from datetime import datetime, timedelta
import os
import json
import resend # Importar la librería resend
import requests # Para hacer llamadas HTTP a la API de Discord
from uuid import uuid4

resend.api_key = os.environ.get("RESEND_API_KEY")

# Helper functions para obtener configuraciones de la base de datos
def get_bot_config(name, default=None):
    """
    Obtiene una configuración del bot desde la base de datos.
    Si no existe o no está activa, devuelve el valor por defecto.
    """
    try:
        config = BotConfiguration.objects.filter(name=name, is_active=True).first()
        return config.value if config else default
    except Exception as e:
        print(f"Error al obtener configuración '{name}': {e}")
        return default

def get_bot_config_int(name, default=None):
    """
    Obtiene una configuración del bot como entero.
    """
    value = get_bot_config(name, default)
    try:
        return int(value) if value else default
    except (ValueError, TypeError):
        print(f"Error al convertir configuración '{name}' a entero: {value}")
        return default

# Las configuraciones ahora se leen desde la base de datos (excepto tokens sensibles)
# DISCORD_BOT_TOKEN se mantiene en variables de entorno por seguridad

# @csrf_exempt es necesario si no estás usando los formularios de Django con tokens CSRF
@csrf_exempt
def generate_invite_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get('email')
        role_id = data.get('roleId')

        if not email or not role_id:
            return JsonResponse({'error': 'Email y Role ID son requeridos.'}, status=400)

        invite_url = ''
        invite_ttl_seconds = get_bot_config_int('invite_ttl_seconds', 86400)
        guild_id = get_bot_config('guild_id')
        welcome_channel_id = get_bot_config('welcome_channel_id')
        discord_bot_token = os.environ.get('DISCORD_BOT_TOKEN')

        if not all([guild_id, welcome_channel_id, discord_bot_token]):
            return JsonResponse({'error': 'Faltan configuraciones de Discord (guild_id, welcome_channel_id en BD) o DISCORD_BOT_TOKEN en variables de entorno.'}, status=500)

        # 1. Verificar si existe un invite PENDING para este email
        existing_invite = Invite.objects.filter(email=email, status='PENDING').order_by('-created_at').first()

        if existing_invite:
            # Verificar si el invite existente aún es válido (no ha expirado)
            if existing_invite.expires_at and datetime.now(existing_invite.expires_at.tzinfo) < existing_invite.expires_at:
                # El invite existente todavía es válido
                print(f"Debug: Se encontró un invite PENDING válido para {email}: {existing_invite.invite_code}")
                invite_url = f"https://discord.gg/{existing_invite.invite_code}"
            else:
                # El invite existente ha expirado, marcar como EXPIRED y generar uno nuevo
                print(f"Debug: Invite PENDING para {email} ({existing_invite.invite_code}) ha expirado. Marcando como EXPIRED.")
                existing_invite.status = 'EXPIRED'
                existing_invite.save()
                existing_invite = None # Para generar un nuevo invite

        if not existing_invite:
            # No hay invite pendiente válido, generar uno nuevo

            # Llamar a la API de Discord directamente para crear el invite
            discord_api_url = f"https://discord.com/api/v10/channels/{welcome_channel_id}/invites"
            headers = {
                "Authorization": f"Bot {discord_bot_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "max_uses": 1,
                "max_age": invite_ttl_seconds,
                "unique": True,
                "temporary": False,
                "reason": f"Invite para {email} (rol {role_id})",
            }

            response = requests.post(discord_api_url, headers=headers, json=payload)
            response.raise_for_status() # Lanza una excepción para errores HTTP
            discord_invite_data = response.json()
            
            invite_code = discord_invite_data['code']
            # invite_url = discord_invite_data['url'] # Eliminamos esta línea
            invite_url = f"https://discord.gg/{invite_code}" # Usamos el código para construir la URL

            created_at = datetime.now()
            expires_at = created_at + timedelta(seconds=invite_ttl_seconds)

            Invite.objects.create(
                invite_code=invite_code,
                role_id=role_id,
                email=email,
                status='PENDING',
                created_at=created_at,
                expires_at=expires_at
            )
            print(f"Debug: Invite real creado: code={invite_code} para {email}")

        # Enviar correo electrónico con Resend
        try:
            email_response = resend.Emails.send({
                "from": "Acme <onboarding@resend.dev>", # Reemplaza con tu dominio verificado
                "to": [email],
                "subject": "Tu invitación a nuestro servidor de Discord",
                "html": f"<strong>¡Hola!</strong><br><br>Has solicitado unirte a nuestro servidor de Discord. Aquí tienes tu enlace de invitación único:<br><a href=\"{invite_url}\">{invite_url}</a><br><br>Este enlace es de un solo uso y te asignará el rol correcto automáticamente.<br><br>¡Te esperamos!",
            })
            print(f"Correo enviado con Resend: {email_response}")

        except Exception as email_error:
            print(f"Error al enviar el correo con Resend: {email_error}")
            # No devolvemos un 500 aquí para no bloquear el flujo si el email es el problema de Resend
            return JsonResponse({'message': 'Invite generado, pero error al enviar el correo.', 'error': str(email_error), 'inviteUrl': invite_url}, status=200)

        return JsonResponse({'message': 'Invite generado y correo enviado exitosamente.', 'inviteUrl': invite_url}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Payload JSON inválido.'}, status=400)
    except requests.exceptions.RequestException as http_error:
        print(f"Error HTTP al llamar a la API de Discord: {http_error}")
        return JsonResponse({'error': 'Error al interactuar con la API de Discord.', 'details': str(http_error)}, status=500)
    except Exception as e:
        print(f"Error en el endpoint /generate-invite: {e}")
        return JsonResponse({'error': 'Error interno del servidor.', 'details': str(e)}, status=500)