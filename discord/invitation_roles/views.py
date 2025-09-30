from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Invite, BotConfiguration, HotmartProduct, HotmartSubscription, HotmartTransaction
from datetime import datetime, timedelta
import os
import json
import resend
import requests
from uuid import uuid4
from decimal import Decimal

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


def process_purchase_event(event_type, event_id, transaction_id, email, status, 
                           purchase_data, buyer_data, product_data, subscription_data, webhook_data):
    try:
        product_id = str(product_data.get('id', 0))
        product_name = product_data.get('name', 'Producto desconocido')
        
        try:
            hotmart_product = HotmartProduct.objects.get(product_id=product_id, is_active=True)
        except HotmartProduct.DoesNotExist:
            error_msg = f"Producto {product_id} no encontrado o inactivo en la BD"
            print(f"⚠️ {error_msg}")
            HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type=event_type,
                email=email,
                status=status,
                raw_webhook_data=webhook_data,
                processed=False,
                error_message=error_msg
            )
            return {'success': False, 'error': error_msg}

        price_data = purchase_data.get('price', {})
        transaction_value = Decimal(str(price_data.get('value', 0)))
        currency = price_data.get('currency_value', 'BRL')

        subscriber_code = subscription_data.get('subscriber', {}).get('code') if subscription_data else None
        plan_id = subscription_data.get('plan', {}).get('id') if subscription_data else None
        plan_name = subscription_data.get('plan', {}).get('name', 'Sin plan') if subscription_data else 'Pago único'
        subscription_status = subscription_data.get('status', 'ACTIVE') if subscription_data else None

        subscription_obj = None
        
        if event_type == 'PURCHASE_APPROVED' and status == 'APPROVED':
            if subscriber_code and hotmart_product.is_subscription:
                subscription_obj, created = HotmartSubscription.objects.get_or_create(
                    subscriber_code=subscriber_code,
                    defaults={
                        'email': email,
                        'product': hotmart_product,
                        'plan_id': str(plan_id),
                        'plan_name': plan_name,
                        'status': 'ACTIVE',
                    }
                )
                
                if not created:
                    subscription_obj.status = 'ACTIVE'
                    subscription_obj.save()
                
                print(f"✅ Suscripción {'creada' if created else 'reactivada'}: {subscriber_code}")
            
            transaction = HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type=event_type,
                email=email,
                subscription=subscription_obj,
                product=hotmart_product,
                status=status,
                transaction_value=transaction_value,
                currency=currency,
                raw_webhook_data=webhook_data,
                processed=True,
                processed_at=timezone.now()
            )
            
            invite_sent = send_discord_invite_email(
                email=email,
                product=hotmart_product,
                subscription=subscription_obj
            )
            
            return {
                'success': True,
                'action': 'purchase_approved',
                'subscription_created': subscription_obj is not None,
                'invite_sent': invite_sent
            }
            
        elif event_type == 'PURCHASE_COMPLETE' and status == 'COMPLETED':
            transaction = HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type=event_type,
                email=email,
                subscription=subscription_obj,
                product=hotmart_product,
                status=status,
                transaction_value=transaction_value,
                currency=currency,
                raw_webhook_data=webhook_data,
                processed=True,
                processed_at=timezone.now()
            )
            
            print(f"✅ Compra completada (período de garantía expirado): {email}")
            return {'success': True, 'action': 'purchase_complete'}
            
        elif event_type == 'PURCHASE_REFUNDED' and status == 'REFUNDED':
            transaction = HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type=event_type,
                email=email,
                subscription=subscription_obj,
                product=hotmart_product,
                status=status,
                transaction_value=transaction_value,
                currency=currency,
                raw_webhook_data=webhook_data,
                processed=True,
                processed_at=timezone.now()
            )
            
            if subscriber_code:
                try:
                    subscription_obj = HotmartSubscription.objects.get(subscriber_code=subscriber_code)
                    subscription_obj.status = 'CANCELLED'
                    subscription_obj.cancellation_date = timezone.now()
                    subscription_obj.save()
                    
                    revoke_discord_roles(subscription_obj)
                    print(f"✅ Roles revocados por reembolso: {email}")
                except HotmartSubscription.DoesNotExist:
                    pass
            
            return {'success': True, 'action': 'purchase_refunded', 'roles_revoked': True}
            
        elif event_type == 'PURCHASE_PROTEST' and status == 'DISPUTE':
            transaction = HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type=event_type,
                email=email,
                subscription=subscription_obj,
                product=hotmart_product,
                status=status,
                transaction_value=transaction_value,
                currency=currency,
                raw_webhook_data=webhook_data,
                processed=True,
                processed_at=timezone.now()
            )
            
            if subscriber_code:
                try:
                    subscription_obj = HotmartSubscription.objects.get(subscriber_code=subscriber_code)
                    subscription_obj.status = 'SUSPENDED'
                    subscription_obj.save()
                    
                    print(f"⚠️ Suscripción suspendida por disputa: {email}")
                except HotmartSubscription.DoesNotExist:
                    pass
            
            return {'success': True, 'action': 'purchase_protest', 'subscription_suspended': True}
        
        return {'success': True, 'action': 'event_logged'}
        
    except Exception as e:
        error_msg = f"Error procesando evento de compra: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        
        HotmartTransaction.objects.create(
            transaction_id=transaction_id,
            hotmart_event_id=event_id,
            event_type=event_type,
            email=email,
            status=status,
            raw_webhook_data=webhook_data,
            processed=False,
            error_message=error_msg
        )
        
        return {'success': False, 'error': error_msg}


def process_subscription_cancellation(event_id, transaction_id, email, subscriber_code, 
                                      subscription_data, subscriber_data, product_data, webhook_data):
    try:
        product_id = str(product_data.get('id', 0))
        
        try:
            subscription = HotmartSubscription.objects.get(subscriber_code=subscriber_code)
            subscription.status = 'CANCELLED'
            subscription.cancellation_date = timezone.now()
            subscription.save()
            
            HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type='SUBSCRIPTION_CANCELLATION',
                email=email,
                subscription=subscription,
                product=subscription.product,
                status='CANCELLED',
                raw_webhook_data=webhook_data,
                processed=True,
                processed_at=timezone.now()
            )
            
            revoke_discord_roles(subscription)
            
            print(f"✅ Suscripción cancelada y roles revocados: {email}")
            return {'success': True, 'action': 'subscription_cancelled', 'roles_revoked': True}
            
        except HotmartSubscription.DoesNotExist:
            error_msg = f"Suscripción no encontrada para subscriber_code: {subscriber_code}"
            print(f"⚠️ {error_msg}")
            
            HotmartTransaction.objects.create(
                transaction_id=transaction_id,
                hotmart_event_id=event_id,
                event_type='SUBSCRIPTION_CANCELLATION',
                email=email,
                status='CANCELLED',
                raw_webhook_data=webhook_data,
                processed=False,
                error_message=error_msg
            )
            
            return {'success': False, 'error': error_msg}
            
    except Exception as e:
        error_msg = f"Error procesando cancelación de suscripción: {str(e)}"
        print(f"❌ {error_msg}")
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

        current_plan_id = str(current_plan.get('id'))
        current_plan_name = current_plan.get('name')
        
        try:
            subscription = HotmartSubscription.objects.get(subscriber_code=subscriber_code)
            old_product = subscription.product
            
            product_data = subscription_data.get('product', {})
            new_product_id = str(product_data.get('id', 0))
            
            try:
                new_product = HotmartProduct.objects.get(product_id=new_product_id, is_active=True)
                
                if new_product.priority > old_product.priority:
                    print(f"⬆️ UPGRADE detectado: {old_product.product_name} → {new_product.product_name}")
                    revoke_discord_roles(subscription)
                    
                    subscription.product = new_product
                    subscription.plan_id = current_plan_id
                    subscription.plan_name = current_plan_name
                    subscription.status = 'ACTIVE'
                    subscription.save()
                    
                    assign_discord_roles(subscription)
                    
                elif new_product.priority < old_product.priority:
                    print(f"⬇️ DOWNGRADE detectado: {old_product.product_name} → {new_product.product_name}")
                    revoke_discord_roles(subscription)
                    
                    subscription.product = new_product
                    subscription.plan_id = current_plan_id
                    subscription.plan_name = current_plan_name
                    subscription.status = 'ACTIVE'
                    subscription.save()
                    
                    assign_discord_roles(subscription)
                    
                else:
                    print(f"🔄 Cambio de plan (misma prioridad): {current_plan_name}")
                    subscription.plan_id = current_plan_id
                    subscription.plan_name = current_plan_name
                    subscription.save()
                
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
                    'new_product': new_product.product_name
                }
                
            except HotmartProduct.DoesNotExist:
                error_msg = f"Producto destino {new_product_id} no encontrado"
                print(f"⚠️ {error_msg}")
                return {'success': False, 'error': error_msg}
                
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
        
        existing_invite = Invite.objects.filter(email=email, status='PENDING').order_by('-created_at').first()
        
        if existing_invite:
            if existing_invite.expires_at and datetime.now(existing_invite.expires_at.tzinfo) < existing_invite.expires_at:
                invite_url = f"https://discord.gg/{existing_invite.invite_code}"
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
            print(f"✅ Invite creado: {invite_code} para {email}")
        
        email_response = resend.Emails.send({
            "from": "Acme <onboarding@resend.dev>",
            "to": [email],
            "subject": f"¡Bienvenido a {product.product_name}! - Acceso a Discord",
            "html": f"""
            <h2>¡Hola!</h2>
            <p>Tu compra de <strong>{product.product_name}</strong> ha sido aprobada exitosamente.</p>
            <p>Aquí tienes tu enlace de invitación único a nuestro servidor de Discord:</p>
            <p><a href="{invite_url}" style="background-color: #5865F2; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">Unirme al Servidor de Discord</a></p>
            <p>Este enlace es de un solo uso y te asignará automáticamente los permisos correctos.</p>
            <p>¡Te esperamos en la comunidad!</p>
            """,
        })
        print(f"✅ Correo de invitación enviado a {email}")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando correo de invitación a {email}: {e}")
        return False


def assign_discord_roles(subscription):
    from .hotmart_utils import notify_discord_webhook
    print(f"🔄 Roles pendientes de asignación para: {subscription.subscriber_code}")
    
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
    
    webhook_url = os.environ.get('DISCORD_NOTIFICATION_WEBHOOK')
    if webhook_url:
        notify_discord_webhook(
            webhook_url=webhook_url,
            title="⚠️ Suscripción Cancelada/Expirada",
            description=f"Usuario con email **{subscription.email}** perdió acceso.",
            color=0xFF0000,
            fields=[
                {"name": "Producto", "value": subscription.product.product_name, "inline": True},
                {"name": "Estado", "value": subscription.status, "inline": True},
                {"name": "Email", "value": subscription.email, "inline": False},
            ]
        )