import os
import discord
import requests
from django.utils import timezone
from asgiref.sync import sync_to_async


@sync_to_async
def get_subscription_by_email(email):
    from .models import HotmartSubscription
    try:
        return HotmartSubscription.objects.filter(
            email=email, 
            status='ACTIVE'
        ).select_related('product').first()
    except Exception as e:
        print(f"❌ Error obteniendo suscripción por email {email}: {e}")
        return None


@sync_to_async
def get_subscription_by_member_id(member_id):
    from .models import HotmartSubscription
    try:
        return HotmartSubscription.objects.filter(
            member_id=str(member_id),
            status='ACTIVE'
        ).select_related('product').first()
    except Exception as e:
        print(f"❌ Error obteniendo suscripción por member_id {member_id}: {e}")
        return None


@sync_to_async
def update_subscription_member_id(subscription_id, member_id):
    from .models import HotmartSubscription
    try:
        subscription = HotmartSubscription.objects.get(id=subscription_id)
        subscription.member_id = str(member_id)
        subscription.last_sync_at = timezone.now()
        subscription.save()
        return True
    except Exception as e:
        print(f"❌ Error actualizando member_id: {e}")
        return False


@sync_to_async
def update_subscription_role(subscription_id, role_id):
    from .models import HotmartSubscription
    try:
        subscription = HotmartSubscription.objects.get(id=subscription_id)
        subscription.current_role_id = str(role_id)
        subscription.last_sync_at = timezone.now()
        subscription.save()
        return True
    except Exception as e:
        print(f"❌ Error actualizando role_id: {e}")
        return False


@sync_to_async
def get_expired_or_cancelled_subscriptions():
    from .models import HotmartSubscription
    try:
        return list(HotmartSubscription.objects.filter(
            status__in=['CANCELLED', 'EXPIRED', 'SUSPENDED', 'PENDING_PAYMENT'],
            member_id__isnull=False
        ).select_related('product'))
    except Exception as e:
        print(f"❌ Error obteniendo suscripciones expiradas: {e}")
        return []


async def assign_hotmart_role_to_member(bot, guild_id, member_id, role_id, subscription):
    try:
        guild = bot.get_guild(int(guild_id))
        if not guild:
            print(f"❌ Guild {guild_id} no encontrado")
            return False
        
        member = guild.get_member(int(member_id))
        if not member:
            print(f"❌ Miembro {member_id} no encontrado en el guild")
            return False
        
        role = guild.get_role(int(role_id))
        if not role:
            print(f"❌ Rol {role_id} no encontrado en el guild")
            return False
        
        if role in member.roles:
            print(f"ℹ️ El miembro {member.name} ya tiene el rol {role.name}")
            return True
        
        bot_member = guild.me
        if role.position >= bot_member.top_role.position:
            print(f"❌ No se puede asignar el rol {role.name}. El rol del bot es igual o inferior")
            return False
        
        await member.add_roles(role)
        print(f"✅ Rol {role.name} asignado a {member.name} (Hotmart: {subscription.product.product_name})")
        
        await update_subscription_role(subscription.id, role_id)
        await update_subscription_member_id(subscription.id, member_id)
        
        return True
        
    except Exception as e:
        print(f"❌ Error asignando rol de Hotmart: {e}")
        import traceback
        traceback.print_exc()
        return False


async def revoke_hotmart_role_from_member(bot, guild_id, member_id, role_id, reason="Suscripción cancelada/expirada"):
    try:
        guild = bot.get_guild(int(guild_id))
        if not guild:
            print(f"❌ Guild {guild_id} no encontrado")
            return False
        
        member = guild.get_member(int(member_id))
        if not member:
            print(f"⚠️ Miembro {member_id} no encontrado en el guild (posiblemente salió del servidor)")
            return True
        
        role = guild.get_role(int(role_id))
        if not role:
            print(f"❌ Rol {role_id} no encontrado en el guild")
            return False
        
        if role not in member.roles:
            print(f"ℹ️ El miembro {member.name} no tiene el rol {role.name}")
            return True
        
        await member.remove_roles(role, reason=reason)
        print(f"✅ Rol {role.name} revocado de {member.name} - Razón: {reason}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error revocando rol de Hotmart: {e}")
        import traceback
        traceback.print_exc()
        return False


async def sync_all_hotmart_subscriptions(bot, guild_id):
    print("🔄 Iniciando sincronización de suscripciones Hotmart...")
    
    expired_subs = await get_expired_or_cancelled_subscriptions()
    
    revoked_count = 0
    for subscription in expired_subs:
        if subscription.member_id and subscription.current_role_id:
            success = await revoke_hotmart_role_from_member(
                bot=bot,
                guild_id=guild_id,
                member_id=subscription.member_id,
                role_id=subscription.current_role_id,
                reason=f"Suscripción {subscription.status.lower()}"
            )
            if success:
                revoked_count += 1
    
    print(f"✅ Sincronización completada. Roles revocados: {revoked_count}")
    return revoked_count


def notify_discord_webhook(webhook_url, title, description, color=0x00FF00, fields=None):
    try:
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": timezone.now().isoformat(),
        }
        
        if fields:
            embed["fields"] = fields
        
        payload = {
            "embeds": [embed]
        }
        
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        print(f"✅ Notificación enviada a Discord webhook")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando notificación a webhook: {e}")
        return False


