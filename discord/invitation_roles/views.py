from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Invite, BotConfiguration, HotmartProduct, HotmartSubscription, HotmartTransaction
from datetime import datetime, timedelta
import os
import json
import smtplib
import ssl
import requests
from email.message import EmailMessage
from uuid import uuid4
from decimal import Decimal, InvalidOperation

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


def send_email_message(to_email, subject, html_body, plain_body):
    """Envía un correo usando Gmail (SMTP + app password)."""
    sender_email = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not sender_email or not app_password:
        raise RuntimeError("GMAIL_ADDRESS o GMAIL_APP_PASSWORD no están configurados.")

    recipients = [to_email] if isinstance(to_email, str) else list(to_email)
    if not recipients:
        raise ValueError("Debe proporcionarse al menos un destinatario.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = ", ".join(recipients)
    msg.set_content(plain_body or "")
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        smtp.login(sender_email, app_password)
        smtp.send_message(msg)


DISCORD_API_BASE_URL = "https://discord.com/api/v10"


def _get_discord_auth_headers():
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        print("? DISCORD_BOT_TOKEN no configurado; no se pueden asignar roles directamente")
        return None
    return {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
    }


def _discord_put_role(guild_id: str, member_id: str, role_id: str) -> bool:
    headers = _get_discord_auth_headers()
    if not headers:
        return False
    url = f"{DISCORD_API_BASE_URL}/guilds/{guild_id}/members/{member_id}/roles/{role_id}"
    response = requests.put(url, headers=headers, timeout=10)
    if response.status_code in (200, 204):
        return True
    print(f"? Error asignando rol {role_id} a miembro {member_id}: {response.status_code} - {response.text}")
    return False


def _discord_delete_role(guild_id: str, member_id: str, role_id: str) -> bool:
    headers = _get_discord_auth_headers()
    if not headers:
        return False
    url = f"{DISCORD_API_BASE_URL}/guilds/{guild_id}/members/{member_id}/roles/{role_id}"
    response = requests.delete(url, headers=headers, timeout=10)
    if response.status_code in (200, 204, 404):
        # 404 indica que el rol ya no estaba asignado; lo tratamos como éxito idempotente
        return True
    print(f"? Error removiendo rol {role_id} de miembro {member_id}: {response.status_code} - {response.text}")
    return False


def _ensure_subscription_role(subscription, target_role_id: str) -> bool:
    member_id = subscription.member_id
    if not member_id:
        print(f"? Suscripción {subscription.subscriber_code} no tiene member_id; no se puede asignar rol directamente")
        return False

    guild_id = get_bot_config('guild_id')
    if not guild_id:
        print("? guild_id no configurado; no se puede asignar rol")
        return False

    target_role_id = str(target_role_id)
    current_role_id = subscription.current_role_id
    visitor_role_id = get_bot_config('visitor_role_id')

    if current_role_id and current_role_id == target_role_id:
        print(f"? Miembro {member_id} ya tiene rol {target_role_id} registrado; no es necesario reasignar")
        return True

    if visitor_role_id and current_role_id and current_role_id == visitor_role_id:
        _discord_delete_role(guild_id, member_id, visitor_role_id)

    if current_role_id and current_role_id not in (None, visitor_role_id, target_role_id):
        _discord_delete_role(guild_id, member_id, current_role_id)

    if _discord_put_role(guild_id, member_id, target_role_id):
        subscription.current_role_id = target_role_id
        subscription.status = 'ACTIVE'
        subscription.last_sync_at = timezone.now()
        subscription.save(update_fields=['current_role_id', 'status', 'last_sync_at'])
        print(f"? Rol {target_role_id} asignado a miembro {member_id} desde la suscripción {subscription.subscriber_code}")
        return True

    return False


def _apply_visitor_role(subscription) -> bool:
    member_id = subscription.member_id
    if not member_id:
        print(f"? Suscripción {subscription.subscriber_code} no tiene member_id; no se puede asignar rol visitante")
        return False

    guild_id = get_bot_config('guild_id')
    if not guild_id:
        print("? guild_id no configurado; no se puede asignar rol visitante")
        return False

    visitor_role_id = get_bot_config('visitor_role_id')
    current_role_id = subscription.current_role_id

    if current_role_id:
        _discord_delete_role(guild_id, member_id, current_role_id)

    visitor_assigned = False
    if visitor_role_id:
        visitor_assigned = _discord_put_role(guild_id, member_id, visitor_role_id)
        if visitor_assigned:
            subscription.current_role_id = str(visitor_role_id)
            print(f"? Rol visitante {visitor_role_id} asignado a miembro {member_id}")
        else:
            subscription.current_role_id = None
    else:
        print("? visitor_role_id no configurado; se deja al miembro sin rol de acceso")
        subscription.current_role_id = None

    subscription.last_sync_at = timezone.now()
    subscription.save(update_fields=['current_role_id', 'last_sync_at'])
    return visitor_assigned


def _collect_hotmart_product_candidates(product_data=None, subscription_data=None, purchase_data=None):
    """Genera posibles identificadores del producto para buscarlo en la BD."""
    candidates = []

    def add_candidate(value, source):
        if value is None:
            return
        normalized = str(value).strip()
        if not normalized:
            return
        candidates.append((normalized, source))

    product_data = product_data or {}
    subscription_data = subscription_data or {}
    purchase_data = purchase_data or {}

    add_candidate(product_data.get('id'), 'product.id')
    add_candidate(product_data.get('ucode'), 'product.ucode')

    content_products = product_data.get('content', {}).get('products', [])
    for item in content_products:
        add_candidate(item.get('id'), 'product.content.products[].id')
        add_candidate(item.get('ucode'), 'product.content.products[].ucode')

    subscription_product = subscription_data.get('product', {})
    add_candidate(subscription_product.get('id'), 'subscription.product.id')
    add_candidate(subscription_product.get('name'), 'subscription.product.name')

    plan_data = subscription_data.get('plan', {})
    add_candidate(plan_data.get('id'), 'subscription.plan.id')
    add_candidate(plan_data.get('name'), 'subscription.plan.name')

    offer_data = purchase_data.get('offer', {})
    add_candidate(offer_data.get('code'), 'purchase.offer.code')
    add_candidate(offer_data.get('coupon_code'), 'purchase.offer.coupon_code')

    add_candidate(purchase_data.get('sckPaymentLink'), 'purchase.sckPaymentLink')

    seen = set()
    deduped = []
    for value, source in candidates:
        if value not in seen:
            deduped.append((value, source))
            seen.add(value)
    return deduped


def resolve_hotmart_product(product_data=None, subscription_data=None, purchase_data=None):
    """Intenta resolver el producto de Hotmart usando distintos identificadores."""
    candidates = _collect_hotmart_product_candidates(product_data, subscription_data, purchase_data)

    for value, source in candidates:
        try:
            product = HotmartProduct.objects.get(product_id=str(value), is_active=True)
            return {
                'product': product,
                'matched_value': str(value),
                'matched_source': source,
                'candidates': candidates,
            }
        except HotmartProduct.DoesNotExist:
            continue

    return {
        'product': None,
        'matched_value': None,
        'matched_source': None,
        'candidates': candidates,
    }


def format_candidate_sources(candidates):
    if not candidates:
        return 'sin identificadores conocidos'
    return ', '.join(f"{value} ({source})" for value, source in candidates)


def to_decimal(value, default=Decimal('0')):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default

TRANSACTION_ALLOWED_STATUSES = {
    'APPROVED',
    'COMPLETED',
    'REFUNDED',
    'DISPUTE',
    'CANCELLED',
    'PENDING',
}

TRANSACTION_STATUS_ALIASES = {
    'PAID': 'APPROVED',
    'UNDER_ANALYSIS': 'DISPUTE',
    'IN_DISPUTE': 'DISPUTE',
    'CHARGEBACK': 'REFUNDED',
    'WAITING_PAYMENT': 'PENDING',
    'PENDING_PAYMENT': 'PENDING',
    'CANCELED': 'CANCELLED',
    'DENIED': 'CANCELLED',
}


def normalize_transaction_status(raw_status):
    candidate = (raw_status or '').upper()
    if candidate in TRANSACTION_ALLOWED_STATUSES:
        return candidate
    return TRANSACTION_STATUS_ALIASES.get(candidate, 'PENDING')


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

        # Enviar correo electronico
        try:
            subject = "Tu invitacion a nuestro servidor de Discord"
            plain_body = (
                "Hola!\n\n"
                "Has solicitado unirte a nuestro servidor de Discord. "
                f"Aqui tienes tu enlace de invitacion unico: {invite_url}\n\n"
                "Este enlace es de un solo uso y te asignara el rol correcto automaticamente.\n\n"
                "Te esperamos!"
            )
            html_body = (
                f'<strong>Hola!</strong><br><br>Has solicitado unirte a nuestro servidor de Discord. ' 
                f'Aqui tienes tu enlace de invitacion unico:<br><a href="{invite_url}">{invite_url}</a><br><br>'
                'Este enlace es de un solo uso y te asignara el rol correcto automaticamente.<br><br>'
                'Te esperamos!'
            )
            send_email_message(email, subject, html_body, plain_body)
            print(f"Correo de invitacion enviado a {email}")

        except Exception as email_error:
            print(f"Error al enviar el correo: {email_error}")
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


@csrf_exempt
def hotmart_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        webhook_data = json.loads(request.body)
        print(f"📩 Webhook de Hotmart recibido: {webhook_data.get('event', 'UNKNOWN')}")
        
        event_type = webhook_data.get('event')
        event_id = webhook_data.get('id')
        data = webhook_data.get('data', {})
        
        if not event_type or not event_id:
            return JsonResponse({'error': 'Webhook inválido: falta event o id'}, status=400)

        if HotmartTransaction.objects.filter(hotmart_event_id=event_id).exists():
            print(f"⚠️ Evento duplicado ignorado: {event_id}")
            return JsonResponse({'message': 'Evento ya procesado'}, status=200)

        transaction_id = None
        email = None
        status = None

        if event_type in ['PURCHASE_APPROVED', 'PURCHASE_COMPLETE', 'PURCHASE_REFUNDED', 'PURCHASE_PROTEST']:
            purchase_data = data.get('purchase', {})
            buyer_data = data.get('buyer', {})
            product_data = data.get('product', {})
            subscription_data = data.get('subscription', {})
            
            transaction_id = purchase_data.get('transaction', f"TRANS_{event_id}")
            email = buyer_data.get('email')
            status = purchase_data.get('status', 'PENDING')
            
            result = process_purchase_event(
                event_type=event_type,
                event_id=event_id,
                transaction_id=transaction_id,
                email=email,
                status=status,
                purchase_data=purchase_data,
                buyer_data=buyer_data,
                product_data=product_data,
                subscription_data=subscription_data,
                webhook_data=webhook_data
            )
            
        elif event_type == 'SUBSCRIPTION_CANCELLATION':
            subscription_data = data.get('subscription', {})
            subscriber_data = data.get('subscriber', {})
            product_data = data.get('product', {})
            
            email = subscriber_data.get('email')
            subscriber_code = subscriber_data.get('code')
            transaction_id = f"CANCEL_{subscriber_code}_{event_id}"
            status = 'CANCELLED'
            
            result = process_subscription_cancellation(
                event_id=event_id,
                transaction_id=transaction_id,
                email=email,
                subscriber_code=subscriber_code,
                subscription_data=subscription_data,
                subscriber_data=subscriber_data,
                product_data=product_data,
                webhook_data=webhook_data
            )
            
        elif event_type == 'SWITCH_PLAN':
            subscription_data = data.get('subscription', {})
            plans_data = data.get('plans', [])
            user_data = subscription_data.get('user', {})
            
            email = user_data.get('email')
            subscriber_code = subscription_data.get('subscriber_code')
            transaction_id = f"SWITCH_{subscriber_code}_{event_id}"
            status = subscription_data.get('status', 'ACTIVE')
            
            result = process_switch_plan(
                event_id=event_id,
                transaction_id=transaction_id,
                email=email,
                subscriber_code=subscriber_code,
                plans_data=plans_data,
                subscription_data=subscription_data,
                webhook_data=webhook_data
            )
            
        elif event_type == 'UPDATE_SUBSCRIPTION_CHARGE_DATE':
            subscription_data = data.get('subscription', {})
            subscriber_data = data.get('subscriber', {})
            
            email = subscriber_data.get('email')
            subscriber_code = subscriber_data.get('code')
            transaction_id = f"UPDATE_{subscriber_code}_{event_id}"
            status = subscription_data.get('status', 'ACTIVE')
            
            result = process_charge_date_update(
                event_id=event_id,
                transaction_id=transaction_id,
                email=email,
                subscriber_code=subscriber_code,
                subscription_data=subscription_data,
                subscriber_data=subscriber_data,
                webhook_data=webhook_data
            )
        else:
            print(f"⚠️ Tipo de evento no manejado: {event_type}")
            return JsonResponse({'message': 'Evento recibido pero no procesado'}, status=200)

        if result.get('success'):
            return JsonResponse({'message': 'Webhook procesado exitosamente', 'details': result}, status=200)
        else:
            return JsonResponse({'message': 'Webhook procesado con errores', 'details': result}, status=200)

    except json.JSONDecodeError:
        print("❌ Error: Payload JSON inválido")
        return JsonResponse({'error': 'Payload JSON inválido'}, status=400)
    except Exception as e:
        print(f"❌ Error procesando webhook de Hotmart: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': 'Error interno del servidor', 'details': str(e)}, status=500)


def process_purchase_event(event_type, event_id, transaction_id, email, status,                            purchase_data, buyer_data, product_data, subscription_data, webhook_data):
    try:
        event_type = (event_type or '').upper()
        status_upper = (status or 'PENDING').upper()
        db_status = normalize_transaction_status(status_upper)
        transaction_id = transaction_id or f"TRANS_{event_id}"

        purchase_data = purchase_data or {}
        buyer_data = buyer_data or {}
        product_data = product_data or {}
        subscription_data = subscription_data or {}

        resolver_info = resolve_hotmart_product(product_data, subscription_data, purchase_data)
        hotmart_product = resolver_info['product']
        candidate_summary = format_candidate_sources(resolver_info['candidates'])

        fallback_email = email or 'unknown@hotmart.local'

        if not hotmart_product:
            error_msg = f"Producto Hotmart no configurado en la BD. Identificadores: {candidate_summary}"
            print(f"?? {error_msg}")
            HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type=event_type,
                email=fallback_email,
                status=db_status,
                raw_webhook_data=webhook_data,
                processed=False,
                error_message=error_msg
            )
            return {'success': False, 'error': error_msg}

        matched_source = resolver_info['matched_source']
        if matched_source:
            print(f"? Producto {hotmart_product.product_name} mapeado usando {matched_source}={resolver_info['matched_value']}")

        if not email:
            error_msg = f"Evento {event_type} sin email del comprador"
            print(f"?? {error_msg}")
            HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type=event_type,
                email=fallback_email,
                product=hotmart_product,
                status=db_status,
                raw_webhook_data=webhook_data,
                processed=False,
                error_message=error_msg
            )
            return {'success': False, 'error': error_msg}

        price_data = purchase_data.get('price') or purchase_data.get('full_price') or purchase_data.get('original_offer_price') or {}
        transaction_value = to_decimal(price_data.get('value'))
        currency = (
            price_data.get('currency_value')
            or purchase_data.get('price', {}).get('currency_value')
            or purchase_data.get('full_price', {}).get('currency_value')
            or 'BRL'
        )

        subscriber_code = subscription_data.get('subscriber', {}).get('code') if subscription_data else None
        plan_data = subscription_data.get('plan', {}) if subscription_data else {}
        plan_id_raw = plan_data.get('id') if plan_data else None
        plan_id_str = str(plan_id_raw) if plan_id_raw is not None else ('ONE_TIME' if not hotmart_product.is_subscription else 'UNKNOWN_PLAN')
        plan_name = plan_data.get('name') or ('Pago único' if not hotmart_product.is_subscription else 'Sin plan')

        subscription_obj = None
        if subscriber_code:
            try:
                subscription_obj = HotmartSubscription.objects.get(subscriber_code=subscriber_code)
            except HotmartSubscription.DoesNotExist:
                subscription_obj = None

        approved_statuses = {'APPROVED', 'PAID'}
        completed_statuses = {'COMPLETED'}
        refunded_statuses = {'REFUNDED', 'CANCELLED', 'CHARGEBACK'}
        protest_statuses = {'DISPUTE', 'UNDER_ANALYSIS'}

        if event_type == 'PURCHASE_APPROVED' and status_upper in approved_statuses:
            if hotmart_product.is_subscription and subscriber_code:
                if subscription_obj:
                    subscription_obj.email = email
                    subscription_obj.product = hotmart_product
                    subscription_obj.plan_id = plan_id_str
                    subscription_obj.plan_name = plan_name
                    subscription_obj.status = 'ACTIVE'
                    subscription_obj.save()
                    print(f"? Suscripción reactivada: {subscriber_code}")
                else:
                    subscription_obj = HotmartSubscription.objects.create(
                        subscriber_code=subscriber_code,
                        email=email,
                        product=hotmart_product,
                        plan_id=plan_id_str,
                        plan_name=plan_name,
                        status='ACTIVE'
                    )
                    print(f"? Suscripción creada: {subscriber_code}")
            elif hotmart_product.is_subscription and not subscriber_code:
                print("?? Compra de suscripción sin subscriber_code, se omite alta en BD")

            transaction = HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type=event_type,
                email=email,
                subscription=subscription_obj,
                product=hotmart_product,
                status=db_status,
                transaction_value=transaction_value,
                currency=currency,
                raw_webhook_data=webhook_data,
                processed=True,
                processed_at=timezone.now()
            )

            role_synced = False
            invite_sent = False
            if subscription_obj and subscription_obj.member_id:
                role_synced = _ensure_subscription_role(subscription_obj, hotmart_product.discord_role_id)

            if not role_synced:
                invite_sent = send_discord_invite_email(
                    email=email,
                    product=hotmart_product,
                    subscription=subscription_obj
                )
            else:
                print(f"? Rol restaurado vía API para {email}")

            return {
                'success': True,
                'action': 'purchase_approved',
                'subscription_created': subscription_obj is not None,
                'role_synced': role_synced,
                'invite_sent': invite_sent
            }

        elif event_type == 'PURCHASE_COMPLETE' and status_upper in completed_statuses:
            HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type=event_type,
                email=email,
                subscription=subscription_obj,
                product=hotmart_product,
                status=db_status,
                transaction_value=transaction_value,
                currency=currency,
                raw_webhook_data=webhook_data,
                processed=True,
                processed_at=timezone.now()
            )

            print(f"? Compra completada para {email}")
            return {'success': True, 'action': 'purchase_complete'}

        elif event_type == 'PURCHASE_REFUNDED' and status_upper in refunded_statuses:
            if not subscription_obj and subscriber_code:
                try:
                    subscription_obj = HotmartSubscription.objects.get(subscriber_code=subscriber_code)
                except HotmartSubscription.DoesNotExist:
                    subscription_obj = None

            refund_status = 'REFUNDED' if status_upper in {'REFUNDED', 'CHARGEBACK'} else normalize_transaction_status(status_upper)

            HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type=event_type,
                email=email,
                subscription=subscription_obj,
                product=hotmart_product,
                status=refund_status,
                transaction_value=transaction_value,
                currency=currency,
                raw_webhook_data=webhook_data,
                processed=True,
                processed_at=timezone.now()
            )

            roles_revoked = False
            if subscription_obj:
                subscription_obj.status = 'CANCELLED'
                subscription_obj.cancellation_date = timezone.now()
                subscription_obj.save()
                roles_revoked = bool(revoke_discord_roles(subscription_obj))
                if roles_revoked:
                    print(f"? Roles revocados por reembolso: {email}")

            return {'success': True, 'action': 'purchase_refunded', 'roles_revoked': roles_revoked}

        
        elif event_type == 'PURCHASE_PROTEST' and status_upper in protest_statuses:
            if not subscription_obj and subscriber_code:
                try:
                    subscription_obj = HotmartSubscription.objects.get(subscriber_code=subscriber_code)
                except HotmartSubscription.DoesNotExist:
                    subscription_obj = None

            protest_status = normalize_transaction_status(status_upper)

            HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type=event_type,
                email=email,
                subscription=subscription_obj,
                product=hotmart_product,
                status=protest_status,
                transaction_value=transaction_value,
                currency=currency,
                raw_webhook_data=webhook_data,
                processed=True,
                processed_at=timezone.now()
            )

            subscription_suspended = False
            if subscription_obj:
                subscription_obj.status = 'SUSPENDED'
                subscription_obj.save()
                subscription_suspended = True
                print(f"?? Suscripción suspendida por disputa: {email}")

            return {'success': True, 'action': 'purchase_protest', 'subscription_suspended': subscription_suspended}

        info_msg = f"Evento {event_type} con estado {status_upper} registrado sin acción específica"
        print(f"? {info_msg}")
        HotmartTransaction.objects.create(
            transaction_id=transaction_id,
            hotmart_event_id=event_id,
            event_type=event_type,
            email=email,
            subscription=subscription_obj,
            product=hotmart_product,
            status=db_status,
            transaction_value=transaction_value,
            currency=currency,
            raw_webhook_data=webhook_data,
            processed=False,
            error_message=info_msg
        )
        return {'success': True, 'action': 'event_logged', 'note': info_msg}

    except Exception as e:
        error_msg = f"Error procesando evento de compra: {str(e)}"
        print(f"? {error_msg}")
        import traceback
        traceback.print_exc()

        HotmartTransaction.objects.create(
            transaction_id=transaction_id or f"TRANS_ERR_{event_id}",
            hotmart_event_id=event_id,
            event_type=event_type,
            email=email or 'unknown@hotmart.local',
            status=normalize_transaction_status(status or 'ERROR'),
            raw_webhook_data=webhook_data,
            processed=False,
            error_message=error_msg
        )

        return {'success': False, 'error': error_msg}


def process_subscription_cancellation(event_id, transaction_id, email, subscriber_code,                                       subscription_data, subscriber_data, product_data, webhook_data):
    try:
        fallback_email = email or 'unknown@hotmart.local'
        resolver_info = resolve_hotmart_product(product_data, subscription_data, None)
        hotmart_product = resolver_info['product']
        if resolver_info['matched_source']:
            print(f"? Cancelación mapeada usando {resolver_info['matched_source']}={resolver_info['matched_value']}")

        if not subscriber_code:
            error_msg = 'Suscripción sin subscriber_code en cancelación'
            print(f"?? {error_msg}")
            HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type='SUBSCRIPTION_CANCELLATION',
                email=fallback_email,
                product=hotmart_product,
                status='CANCELLED',
                raw_webhook_data=webhook_data,
                processed=False,
                error_message=error_msg
            )
            return {'success': False, 'error': error_msg}

        try:
            subscription = HotmartSubscription.objects.get(subscriber_code=subscriber_code)
            subscription.status = 'CANCELLED'
            subscription.cancellation_date = timezone.now()
            subscription.save()

            HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type='SUBSCRIPTION_CANCELLATION',
                email=email or subscription.email,
                subscription=subscription,
                product=subscription.product,
                status='CANCELLED',
                raw_webhook_data=webhook_data,
                processed=True,
                processed_at=timezone.now()
            )

            roles_revoked = bool(revoke_discord_roles(subscription))

            print(f"? Suscripción cancelada y roles revocados: {subscription.email}")
            return {'success': True, 'action': 'subscription_cancelled', 'roles_revoked': roles_revoked}

        except HotmartSubscription.DoesNotExist:
            error_msg = f"Suscripción no encontrada para subscriber_code: {subscriber_code}"
            print(f"?? {error_msg}")

            HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type='SUBSCRIPTION_CANCELLATION',
                email=fallback_email,
                product=hotmart_product,
                status='CANCELLED',
                raw_webhook_data=webhook_data,
                processed=False,
                error_message=error_msg
            )

            return {'success': False, 'error': error_msg}

    except Exception as e:
        error_msg = f"Error procesando cancelación de suscripción: {str(e)}"
        print(f"? {error_msg}")
        return {'success': False, 'error': error_msg}


def process_switch_plan(event_id, transaction_id, email, subscriber_code, 
                       plans_data, subscription_data, webhook_data):
    try:
        current_plan = next((p for p in plans_data if p.get('current')), None)
        old_plan = next((p for p in plans_data if not p.get('current')), None)
        
        if not current_plan:
            error_msg = "No se encontró el plan actual en SWITCH_PLAN"
            print(f"⚠️ {error_msg}")
            return {'success': False, 'error': error_msg}

        current_plan_id_raw = current_plan.get('id')
        current_plan_id = str(current_plan_id_raw) if current_plan_id_raw is not None else 'UNKNOWN_PLAN'
        current_plan_name = current_plan.get('name') or 'Plan sin nombre'

        if not subscriber_code:
            error_msg = 'SWITCH_PLAN sin subscriber_code'
            print(f'?? {error_msg}')
            return {'success': False, 'error': error_msg}

        try:
            subscription = HotmartSubscription.objects.get(subscriber_code=subscriber_code)
            old_product = subscription.product
            
            product_data = subscription_data.get('product', {})
            resolver_info = resolve_hotmart_product(product_data, subscription_data, None)
            new_product = resolver_info['product']

            if not new_product:
                candidate_summary = format_candidate_sources(resolver_info['candidates'])
                error_msg = f"Producto destino no encontrado. Identificadores: {candidate_summary}"
                print(f"?? {error_msg}")
                return {'success': False, 'error': error_msg}

            if resolver_info['matched_source']:
                print(f"? Cambio de plan mapeado usando {resolver_info['matched_source']}={resolver_info['matched_value']}")

            if new_product.priority > old_product.priority:
                print(f"⬆️ UPGRADE detectado: {old_product.product_name} -> {new_product.product_name}")
            elif new_product.priority < old_product.priority:
                print(f"⬇️ DOWNGRADE detectado: {old_product.product_name} -> {new_product.product_name}")
            else:
                print(f"🔄 Cambio de plan (misma prioridad): {current_plan_name}")

            subscription.product = new_product
            subscription.plan_id = current_plan_id
            subscription.plan_name = current_plan_name
            subscription.status = 'ACTIVE'
            subscription.save(update_fields=['product', 'plan_id', 'plan_name', 'status'])

            role_synced = False
            invite_sent = False
            if subscription.member_id:
                role_synced = _ensure_subscription_role(subscription, new_product.discord_role_id)

            if not role_synced:
                invite_sent = send_discord_invite_email(email=email, product=new_product, subscription=subscription)

            HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type='SWITCH_PLAN',
                email=email,
                subscription=subscription,
                product=new_product,
                status='APPROVED',
                raw_webhook_data=webhook_data,
                processed=True,
                processed_at=timezone.now()
            )

            return {
                'success': True,
                'action': 'plan_switched',
                'old_product': old_product.product_name,
                'new_product': new_product.product_name,
                'role_synced': role_synced,
                'invite_sent': invite_sent
            }

        except HotmartSubscription.DoesNotExist:
            error_msg = f"Suscripción no encontrada: {subscriber_code}"
            print(f"⚠️ {error_msg}")
            return {'success': False, 'error': error_msg}
            
    except Exception as e:
        error_msg = f"Error procesando cambio de plan: {str(e)}"
        print(f"❌ {error_msg}")
        return {'success': False, 'error': error_msg}


def process_charge_date_update(event_id, transaction_id, email, subscriber_code, 
                               subscription_data, subscriber_data, webhook_data):
    try:
        if not subscriber_code:
            error_msg = 'UPDATE_SUBSCRIPTION_CHARGE_DATE sin subscriber_code'
            print(f'?? {error_msg}')
            return {'success': False, 'error': error_msg}

        try:
            subscription = HotmartSubscription.objects.get(subscriber_code=subscriber_code)
            
            date_next_charge = subscription_data.get('date_next_charge')
            if date_next_charge:
                from dateutil import parser
                subscription.next_charge_date = parser.parse(date_next_charge)
                subscription.save()
            
            HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type='UPDATE_SUBSCRIPTION_CHARGE_DATE',
                email=email,
                subscription=subscription,
                product=subscription.product,
                status='APPROVED',
                raw_webhook_data=webhook_data,
                processed=True,
                processed_at=timezone.now()
            )
            
            print(f"✅ Fecha de cobro actualizada: {email}")
            return {'success': True, 'action': 'charge_date_updated'}
            
        except HotmartSubscription.DoesNotExist:
            error_msg = f"Suscripción no encontrada: {subscriber_code}"
            print(f"⚠️ {error_msg}")
            return {'success': False, 'error': error_msg}
            
    except Exception as e:
        error_msg = f"Error actualizando fecha de cobro: {str(e)}"
        print(f"❌ {error_msg}")
        return {'success': False, 'error': error_msg}


def send_discord_invite_email(email, product, subscription=None):
    try:
        role_id = product.discord_role_id

        invite_url = ""
        existing_invite = Invite.objects.filter(email=email, status='PENDING').order_by('-created_at').first()

        if existing_invite:
            if existing_invite.expires_at and datetime.now(existing_invite.expires_at.tzinfo) < existing_invite.expires_at:
                invite_url = f"https://discord.gg/{existing_invite.invite_code}"
                if subscription:
                    subscription.current_role_id = None
                    subscription.last_sync_at = timezone.now()
                    subscription.save(update_fields=['current_role_id', 'last_sync_at'])
                print(f"✅ Usando invite existente para {email}: {existing_invite.invite_code}")
            else:
                existing_invite.status = 'EXPIRED'
                existing_invite.save()
                existing_invite = None
        
        if not existing_invite:
            invite_ttl_seconds = get_bot_config_int('invite_ttl_seconds', 604800)
            guild_id = get_bot_config('guild_id')
            welcome_channel_id = get_bot_config('welcome_channel_id')
            discord_bot_token = os.environ.get('DISCORD_BOT_TOKEN')
            
            if not all([guild_id, welcome_channel_id, discord_bot_token]):
                print("❌ Faltan configuraciones de Discord")
                return False
            
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
                "reason": f"Hotmart: {email} - {product.product_name}",
            }
            
            response = requests.post(discord_api_url, headers=headers, json=payload)
            response.raise_for_status()
            discord_invite_data = response.json()
            
            invite_code = discord_invite_data['code']
            invite_url = f"https://discord.gg/{invite_code}"
            
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
            if subscription:
                subscription.current_role_id = None
                subscription.last_sync_at = timezone.now()
                subscription.save(update_fields=['current_role_id', 'last_sync_at'])
            print(f"✅ Invite creado: {invite_code} para {email}")
        
        if not invite_url:
            print('No se pudo generar un enlace de invitacion valido.')
            return False

        subject = f"Bienvenido a IMAX - Acceso a la Comunidad de Discord"
        plain_body = (
            "Bienvenido a IMAX.\n\n"
            "Aqui tienes el enlace para acceso a la comunidad de alumnos en Discord, "
            "donde tendras acceso personalizado segun el nivel de programa al que hayas entrado.\n\n"
            f"Enlace de invitacion: {invite_url}\n\n"
            "Este enlace es de un solo uso y te asignara automaticamente los permisos correctos.\n\n"
            "Si no tienes Discord instalado, puedes descargarlo aqui:\n"
            "Android: https://play.google.com/store/apps/details?id=com.discord&hl=es\n"
            "iOS: https://apps.apple.com/es/app/discord-juega-y-pasa-el-rato/id985746746\n"
            "Descarga general: https://discord.com/download\n\n"
            "Te esperamos en la comunidad!"
        )
        html_body = (
            '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">'
            '<h2 style="color: #333;">Bienvenido a IMAX</h2>'
            '<p style="color: #666; line-height: 1.6;">'
            'Aqui tienes el enlace para acceso a la comunidad de alumnos en Discord, '
            'donde tendras acceso personalizado segun el nivel de programa al que hayas entrado.'
            '</p>'
            f'<p style="text-align: center; margin: 30px 0;">'
            f'<a href="{invite_url}" style="background-color: #5865F2; color: white; padding: 15px 30px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: bold; font-size: 16px;">ENTRAR AHORA A LA COMUNIDAD</a>'
            '</p>'
            '<p style="color: #666; font-size: 12px; margin-top: 30px;">'
            'Este enlace es de un solo uso y te asignara automaticamente los permisos correctos.'
            '</p>'
            '<hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">'
            '<p style="color: #666; font-size: 14px; margin-bottom: 10px;">'
            '<strong>¿No tienes Discord instalado?</strong>'
            '</p>'
            '<p style="color: #666; font-size: 14px; line-height: 1.8;">'
            '<a href="https://play.google.com/store/apps/details?id=com.discord&hl=es" style="color: #5865F2; text-decoration: none; margin-right: 15px;">📱 Descargar para Android</a><br>'
            '<a href="https://apps.apple.com/es/app/discord-juega-y-pasa-el-rato/id985746746" style="color: #5865F2; text-decoration: none; margin-right: 15px;">📱 Descargar para iOS</a><br>'
            '<a href="https://discord.com/download" style="color: #5865F2; text-decoration: none;">💻 Descargar para PC/Mac</a>'
            '</p>'
            '<p style="color: #666; margin-top: 30px;">Te esperamos en la comunidad!</p>'
            '</div>'
        )
        send_email_message(email, subject, html_body, plain_body)
        print(f"Correo de invitacion enviado a {email}")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando correo de invitación a {email}: {e}")
        return False


def assign_discord_roles(subscription):
    from .hotmart_utils import notify_discord_webhook
    print(f"🔄 Roles pendientes de asignación para: {subscription.subscriber_code}")

    if subscription.product and subscription.product.discord_role_id and subscription.member_id:
        _ensure_subscription_role(subscription, subscription.product.discord_role_id)

    webhook_url = os.environ.get('DISCORD_NOTIFICATION_WEBHOOK')
    if webhook_url:
        notify_discord_webhook(
            webhook_url=webhook_url,
            title="🎉 Nueva Suscripción Activa",
            description=f"Usuario con email **{subscription.email}** activó suscripción.",
            color=0x00FF00,
            fields=[
                {"name": "Producto", "value": subscription.product.product_name, "inline": True},
                {"name": "Plan", "value": subscription.plan_name, "inline": True},
                {"name": "Email", "value": subscription.email, "inline": False},
            ]
        )


def revoke_discord_roles(subscription):
    from .hotmart_utils import notify_discord_webhook
    print(f"🔄 Roles pendientes de revocación para: {subscription.subscriber_code}")

    visitor_assigned = False
    try:
        visitor_assigned = _apply_visitor_role(subscription)
    except Exception as role_error:
        print(f"? Error aplicando rol visitante: {role_error}")

    webhook_url = os.environ.get('DISCORD_NOTIFICATION_WEBHOOK')
    if webhook_url:
        extra_note = "Rol visitante asignado" if visitor_assigned else "Rol visitante no asignado"
        notify_discord_webhook(
            webhook_url=webhook_url,
            title="⚠️ Suscripción Cancelada/Expirada",
            description=f"Usuario con email **{subscription.email}** perdió acceso. {extra_note}.",
            color=0xFF0000,
            fields=[
                {"name": "Producto", "value": subscription.product.product_name, "inline": True},
                {"name": "Estado", "value": subscription.status, "inline": True},
                {"name": "Email", "value": subscription.email, "inline": False},
            ]
        )

    return visitor_assigned
