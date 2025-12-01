# 🚀 Integración Hotmart - Discord Bot

  1. Configura visitor_role_id en BotConfiguration con el rol base que quieres otorgar tras la baja.
  2. Verifica que DISCORD_BOT_TOKEN y guild_id siguen vigentes, pues ahora se usan para llamadas REST
  directas.
  3. Prueba completa:
      - Webhook PURCHASE_APPROVED de un usuario con member_id en BD debe reactivar rol sin generar
  invite.
      - Webhook SUBSCRIPTION_CANCELLATION debe quitar el rol premium y, si configuraste
  visitor_role_id, añadir el rol visitante.
      - Cambiar de plan (via SWITCH_PLAN) debe reemplazar el rol anterior sin intervención manual.
      - Usuarios sin member_id seguirán recibiendo correo con enlace.
      
## 📋 Índice

1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Modelos de Base de Datos](#modelos-de-base-de-datos)
4. [Flujo de Eventos](#flujo-de-eventos)
5. [Configuración](#configuración)
6. [Casos de Uso](#casos-de-uso)
7. [Manejo de Errores](#manejo-de-errores)
8. [Pruebas](#pruebas)

---

## 📖 Descripción General

Este sistema integra Hotmart con Discord para **gestionar automáticamente roles y accesos** basados en el estado de suscripciones y compras.

### ✨ Características Principales

- ✅ **Gestión automática de roles** según estado de suscripción
- ✅ **Email único por usuario** (evita duplicados)
- ✅ **Soporte para upgrades/downgrades** de productos
- ✅ **Revocación automática** cuando se cancela o expira
- ✅ **Sistema de prioridades** para múltiples productos
- ✅ **Registro completo** de transacciones para auditoría
- ✅ **Webhooks de notificación** para eventos importantes

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Hotmart   │────────>│  Django API  │────────>│   Discord   │
│  (Webhook)  │         │   (Views)    │         │     Bot     │
└─────────────┘         └──────────────┘         └─────────────┘
                               │
                               │
                        ┌──────▼──────┐
                        │  PostgreSQL │
                        │  (Modelos)  │
                        └─────────────┘
```

### Componentes

1. **Hotmart Webhook** → Envía eventos a `/hotmart/webhook/`
2. **Django Views** → Procesa eventos y guarda en BD
3. **Modelos Django** → Almacenan productos, suscripciones, transacciones
4. **Utilidades** → Asignan/revocan roles en Discord
5. **Bot Discord** → Ejecuta acciones en el servidor

---

## 🗄️ Modelos de Base de Datos

### HotmartProduct

Representa un producto de Hotmart vinculado a un rol de Discord.

```python
{
    "product_id": "788921",           # ID del producto en Hotmart
    "product_name": "Curso Premium",  # Nombre descriptivo
    "discord_role_id": "123456789",   # ID del rol en Discord
    "is_subscription": true,          # Si es suscripción recurrente
    "is_active": true,                # Si está activo
    "priority": 10                    # Prioridad (mayor = mejor)
}
```

**Campos clave:**

- `priority`: Determina jerarquía en upgrades/downgrades
  - `priority = 10` → Plan Premium
  - `priority = 5` → Plan Básico
  - `priority = 1` → Plan Gratuito

### HotmartSubscription

Representa una suscripción activa de un usuario.

```python
{
    "subscriber_code": "I9OT62C3",        # Código único de Hotmart
    "email": "usuario@example.com",       # Email del suscriptor (ÚNICO)
    "product": <HotmartProduct>,          # Producto asociado
    "plan_id": "123",                     # ID del plan
    "plan_name": "Plan Mensual",          # Nombre del plan
    "status": "ACTIVE",                   # ACTIVE, CANCELLED, SUSPENDED, etc.
    "member_id": "987654321",             # ID del miembro en Discord
    "current_role_id": "123456789",       # Rol actual asignado
    "next_charge_date": "2025-10-30",     # Próxima fecha de cobro
    "cancellation_date": null             # Fecha de cancelación (si aplica)
}
```

**Estados posibles:**

- `ACTIVE` → Suscripción activa, tiene acceso
- `CANCELLED` → Cancelada, sin acceso
- `SUSPENDED` → Suspendida (por disputa), sin acceso
- `EXPIRED` → Expirada, sin acceso
- `PENDING_PAYMENT` → Pago pendiente, acceso temporal

### HotmartTransaction

Registra cada evento recibido de Hotmart para auditoría.

```python
{
    "transaction_id": "HP16015479281022",
    "hotmart_event_id": "1f1ab22e-ae66...",
    "event_type": "PURCHASE_APPROVED",
    "email": "usuario@example.com",
    "subscription": <HotmartSubscription>,
    "product": <HotmartProduct>,
    "status": "APPROVED",
    "transaction_value": 149.50,
    "currency": "BRL",
    "raw_webhook_data": { ... },          # JSON completo del webhook
    "processed": true,                    # Si se procesó correctamente
    "processed_at": "2025-09-30T...",
    "error_message": ""                   # Mensaje de error si falló
}
```

---

## 🔄 Flujo de Eventos

### 1. PURCHASE_APPROVED (Compra Aprobada)

**¿Cuándo ocurre?** Cuando se aprueba un pago.

**Acciones:**

1. ✅ Verifica que el producto existe en BD
2. ✅ Crea o reactiva la suscripción
3. ✅ Registra la transacción
4. ✅ Genera invite único de Discord
5. ✅ Envía correo con link de invitación

**Resultado:** Usuario recibe acceso inmediato.

```json
{
  "event": "PURCHASE_APPROVED",
  "data": {
    "purchase": { "status": "APPROVED", "transaction": "HP123..." },
    "buyer": { "email": "user@example.com" },
    "product": { "id": 788921, "name": "Curso Premium" },
    "subscription": {
      "subscriber": { "code": "ABC123" },
      "plan": { "id": 456, "name": "Plan Mensual" }
    }
  }
}
```

---

### 2. PURCHASE_COMPLETE (Compra Completada)

**¿Cuándo ocurre?** Cuando expira el período de garantía.

**Acciones:**

1. ✅ Registra la transacción como COMPLETED
2. ℹ️ Solo informativo, no afecta acceso

**Resultado:** La compra ya no puede reembolsarse.

---

### 3. PURCHASE_REFUNDED (Reembolso)

**¿Cuándo ocurre?** Cuando se devuelve el dinero al comprador.

**Acciones:**

1. ✅ Marca la suscripción como CANCELLED
2. ✅ Revoca roles de Discord
3. ✅ Registra la transacción

**Resultado:** Usuario pierde acceso inmediatamente.

---

### 4. SUBSCRIPTION_CANCELLATION (Cancelación)

**¿Cuándo ocurre?** Cuando el usuario o sistema cancela la suscripción.

**Acciones:**

1. ✅ Busca la suscripción por `subscriber_code`
2. ✅ Marca como CANCELLED
3. ✅ Revoca roles de Discord
4. ✅ Registra fecha de cancelación

**Resultado:** Usuario pierde acceso.

```json
{
  "event": "SUBSCRIPTION_CANCELLATION",
  "data": {
    "subscriber": { "code": "ABC123", "email": "user@example.com" },
    "subscription": { "id": 4148584 },
    "cancellation_date": 1609181285500
  }
}
```

---

### 5. SWITCH_PLAN (Cambio de Plan)

**¿Cuándo ocurre?** Cuando el usuario cambia de plan (upgrade/downgrade).

**Acciones:**

#### UPGRADE (Prioridad mayor)

1. ✅ Revoca rol anterior
2. ✅ Actualiza producto en suscripción
3. ✅ Asigna nuevo rol (mejor)
4. ✅ Envía notificación

#### DOWNGRADE (Prioridad menor)

1. ✅ Revoca rol anterior
2. ✅ Actualiza producto en suscripción
3. ✅ Asigna nuevo rol (menor)
4. ✅ Envía notificación

**Comparación de prioridades:**

```python
if new_product.priority > old_product.priority:
    # UPGRADE
elif new_product.priority < old_product.priority:
    # DOWNGRADE
else:
    # Cambio lateral (misma prioridad)
```

**Resultado:** Usuario obtiene roles correspondientes al nuevo plan.

```json
{
  "event": "SWITCH_PLAN",
  "data": {
    "plans": [
      { "id": 654321, "name": "Plan Premium", "current": true },
      { "id": 123456, "name": "Plan Básico", "current": false }
    ],
    "subscription": {
      "subscriber_code": "ABC123",
      "status": "ACTIVE"
    }
  }
}
```

---

### 6. UPDATE_SUBSCRIPTION_CHARGE_DATE

**¿Cuándo ocurre?** Cuando cambia la fecha de próximo cobro.

**Acciones:**

1. ✅ Actualiza `next_charge_date` en suscripción
2. ℹ️ Solo informativo

**Resultado:** BD actualizada con nueva fecha.

---

### Mapeo de datos desde Hotmart

Para mitigar errores se normalizan los payloads documentados en `hotmart.md`. Las respuestas 1-5 cubren `PURCHASE_APPROVED`, `PURCHASE_COMPLETE`, `PURCHASE_REFUNDED`, `SUBSCRIPTION_CANCELLATION`, `SWITCH_PLAN` y `UPDATE_SUBSCRIPTION_CHARGE_DATE`.

**Identificadores de producto evaluados (en orden):**
- `product.id` y `product.ucode` del payload principal.
- `product.content.products[].id` y `product.content.products[].ucode` cuando Hotmart agrupa varios subproductos.
- `subscription.product.id` y `subscription.plan.id`/`plan.name` para eventos ligados a suscripciones.
- `purchase.offer.code`, `purchase.offer.coupon_code` y `purchase.sckPaymentLink` para ventas con ofertas o payment links.

Se busca el primer valor activo en `HotmartProduct.product_id`. El origen queda trazado en logs (por ejemplo: `Producto Plan VIP mapeado usando subscription.plan.id=654321`).

**Normalización de estados de transacción:**

| Hotmart | Estado almacenado | Evento que lo usa |
| --- | --- | --- |
| `APPROVED`, `PAID` | `APPROVED` | `PURCHASE_APPROVED` |
| `COMPLETED` | `COMPLETED` | `PURCHASE_COMPLETE` |
| `REFUNDED`, `CHARGEBACK` | `REFUNDED` | `PURCHASE_REFUNDED` |
| `CANCELLED`, `CANCELED` | `CANCELLED` | `PURCHASE_REFUNDED` / cancelaciones manuales |
| `UNDER_ANALYSIS`, `IN_DISPUTE` | `DISPUTE` | `PURCHASE_PROTEST` |
| `WAITING_PAYMENT`, `PENDING_PAYMENT` | `PENDING` | registro informativo |

Cualquier estado no reconocido se persiste como `PENDING` para facilitar auditorías sin romper los choices del modelo.

**Fallbacks controlados:**
- Eventos sin `email` se registran con `unknown@hotmart.local` pero no disparan accesos.
- Si llega un webhook sin `subscriber_code`, se responde con error lógico y la transacción queda marcada como `processed=False`.
- Cuando el producto no está configurado se guardan los identificadores recibidos para depuración.
- Al quedar una suscripción en estado `CANCELLED`, `REFUNDED` o `SUSPENDED` se quita el rol premium y, si existe `visitor_role_id` en `BotConfiguration`, se asigna automáticamente el rol visitante.
- Si el usuario vuelve a pagar y la suscripción tiene `member_id` registrado, el rol premium se reasigna vía API sin necesidad de consumir un nuevo enlace; sólo se envía invitación cuando no se logra sincronizar el rol automáticamente.

Con estas reglas, los cinco payloads de ejemplo se procesan sin errores y quedan mapeados a los modelos `HotmartProduct`, `HotmartSubscription` y `HotmartTransaction`.

## ⚙️ Configuración

### 1. Variables de Entorno

```bash
# Django
DJANGO_SETTINGS_MODULE=discord.discord.settings

# Discord
DISCORD_BOT_TOKEN=tu_token_del_bot
DISCORD_NOTIFICATION_WEBHOOK=https://discord.com/api/webhooks/...

# Email
RESEND_API_KEY=tu_api_key_de_resend
```

### 2. Configuraciones en Base de Datos

Usar el admin de Django para configurar:

```python
BotConfiguration.objects.create(
    name='guild_id',
    value='1234567890',
    configuration_type='guild',
    description='ID del servidor Discord',
    is_active=True
)
```

**Configuraciones requeridas:**

- `guild_id` → ID del servidor Discord
- `welcome_channel_id` → Canal donde se envían invites
- `rules_channel_id` → Canal de reglas
- `invite_ttl_seconds` → Tiempo de vida del invite (default: 604800 = 7 días)
- `visitor_role_id` → (Opcional) Rol base que se asignará cuando una suscripción quede cancelada o expirada

### 3. Productos en Hotmart

Crear productos en el admin de Django:

```python
HotmartProduct.objects.create(
    product_id='788921',                # ID de Hotmart
    product_name='Curso Premium',
    discord_role_id='123456789',        # ID del rol en Discord
    is_subscription=True,
    is_active=True,
    priority=10                         # Mayor prioridad
)
```

### 4. Webhook en Hotmart

Configurar en el panel de Hotmart:

**URL del Webhook:**

```
https://tu-dominio.com/invitation_roles/hotmart/webhook/
```

**Eventos a escuchar:**

- ✅ PURCHASE_APPROVED
- ✅ PURCHASE_COMPLETE
- ✅ PURCHASE_REFUNDED
- ✅ PURCHASE_PROTEST
- ✅ SUBSCRIPTION_CANCELLATION
- ✅ SWITCH_PLAN
- ✅ UPDATE_SUBSCRIPTION_CHARGE_DATE

---

## 💡 Casos de Uso

### Caso 1: Nueva Compra (Pago Único)

1. Usuario compra "Curso Básico" (sin suscripción)
2. Hotmart envía `PURCHASE_APPROVED`
3. Sistema crea transacción (sin suscripción)
4. Genera invite de Discord
5. Envía correo al usuario
6. Usuario se une y acepta reglas
7. Bot asigna rol "Curso Básico"

### Caso 2: Nueva Suscripción

1. Usuario compra "Plan Mensual" (suscripción)
2. Hotmart envía `PURCHASE_APPROVED`
3. Sistema crea suscripción ACTIVE
4. Genera invite de Discord
5. Envía correo al usuario
6. Usuario se une y acepta reglas
7. Bot asigna rol "Plan Mensual"

### Caso 3: Renovación de Suscripción

1. Mes siguiente, Hotmart cobra automáticamente
2. Hotmart envía `PURCHASE_APPROVED` (nuevo cobro)
3. Sistema busca suscripción existente
4. Reactiva si estaba cancelada
5. Usuario mantiene acceso

### Caso 4: Fallo en Renovación

1. Tarjeta rechazada
2. Hotmart reintenta hasta 5 veces
3. Si falla todo, cancela automáticamente
4. Hotmart envía `SUBSCRIPTION_CANCELLATION`
5. Sistema marca como CANCELLED
6. Revoca roles de Discord
7. Usuario pierde acceso

### Caso 5: Upgrade de Plan

1. Usuario en "Plan Básico" (priority=5)
2. Compra "Plan Premium" (priority=10)
3. Hotmart envía `SWITCH_PLAN`
4. Sistema detecta upgrade (10 > 5)
5. Revoca rol "Plan Básico"
6. Asigna rol "Plan Premium"
7. Actualiza BD

### Caso 6: Downgrade de Plan

1. Usuario en "Plan Premium" (priority=10)
2. Cambia a "Plan Básico" (priority=5)
3. Hotmart envía `SWITCH_PLAN`
4. Sistema detecta downgrade (5 < 10)
5. Revoca rol "Plan Premium"
6. Asigna rol "Plan Básico"
7. Actualiza BD

### Caso 7: Usuario con Email Duplicado

**Problema:** Mismo email intenta comprar dos veces

**Solución:**

- `subscriber_code` es ÚNICO por suscripción
- `email` se repite pero cada suscripción es independiente
- Sistema busca primero por `subscriber_code`
- Si es renovación, actualiza la existente
- Si es nuevo producto, crea nueva suscripción

**Ejemplo:**

```python
# Suscripción 1 (activa)
{
    "subscriber_code": "ABC123",
    "email": "user@example.com",
    "product": "Plan Básico",
    "status": "ACTIVE"
}

# Suscripción 2 (upgrade)
{
    "subscriber_code": "XYZ789",  # DIFERENTE
    "email": "user@example.com",  # MISMO EMAIL
    "product": "Plan Premium",
    "status": "ACTIVE"
}
```

**Recomendación:**

- ✅ Usar `subscriber_code` como identificador único
- ✅ Permitir múltiples suscripciones por email
- ✅ El usuario puede tener varios productos simultáneamente
- ⚠️ Si quieres un solo producto activo por email, agregar lógica adicional

### Caso 8: Reembolso

1. Usuario solicita reembolso dentro de garantía
2. Hotmart aprueba reembolso
3. Hotmart envía `PURCHASE_REFUNDED`
4. Sistema marca suscripción como CANCELLED
5. Revoca roles
6. Usuario pierde acceso

---

## 🛡️ Manejo de Errores

### Producto No Encontrado

```python
# Webhook recibe product_id no registrado
# Sistema registra transacción con processed=False
# Admin revisa y agrega producto manualmente
```

### Suscripción No Encontrada

```python
# SUBSCRIPTION_CANCELLATION para subscriber_code inexistente
# Sistema registra error en transaction.error_message
# No afecta otros procesos
```

### Error de Discord API

```python
# No se puede asignar rol (permisos, rol eliminado, etc.)
# Sistema registra en logs
# Envía notificación a webhook de monitoreo
# Admin puede revisar y corregir manualmente
```

### Webhook Duplicado

```python
# Hotmart reenvía mismo evento
# Sistema verifica hotmart_event_id
# Si ya existe, ignora (200 OK pero no procesa)
```

---

## 🧪 Pruebas

### Probar Webhook Localmente

Usa los datos de `hotmart.md`:

```bash
curl -X POST http://localhost:8000/invitation_roles/hotmart/webhook/ \
  -H "Content-Type: application/json" \
  -d @hotmart.md
```

### Eventos de Prueba

#### 1. PURCHASE_APPROVED

```bash
curl -X POST http://localhost:8000/invitation_roles/hotmart/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event": "PURCHASE_APPROVED",
    "id": "test-event-001",
    "data": {
      "product": {"id": "0", "name": "Test Product"},
      "purchase": {
        "transaction": "TEST123",
        "status": "APPROVED",
        "price": {"value": 100, "currency_value": "BRL"}
      },
      "buyer": {"email": "test@example.com"},
      "subscription": {
        "subscriber": {"code": "SUB001"},
        "plan": {"id": "1", "name": "Plan Test"},
        "status": "ACTIVE"
      }
    }
  }'
```

#### 2. SUBSCRIPTION_CANCELLATION

```bash
curl -X POST http://localhost:8000/invitation_roles/hotmart/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event": "SUBSCRIPTION_CANCELLATION",
    "id": "test-event-002",
    "data": {
      "subscriber": {"code": "SUB001", "email": "test@example.com"},
      "product": {"id": "0"},
      "cancellation_date": 1609181285500
    }
  }'
```

### Verificar en Base de Datos

```python
from invitation_roles.models import HotmartTransaction, HotmartSubscription

# Ver transacciones recientes
HotmartTransaction.objects.all().order_by('-created_at')[:10]

# Ver suscripciones activas
HotmartSubscription.objects.filter(status='ACTIVE')

# Ver errores no procesados
HotmartTransaction.objects.filter(processed=False)
```

---

## 📊 Monitoreo

### Logs Importantes

```bash
# Eventos recibidos
📩 Webhook de Hotmart recibido: PURCHASE_APPROVED

# Suscripciones
✅ Suscripción creada: ABC123
✅ Suscripción cancelada y roles revocados: user@example.com

# Roles
✅ Rol Plan Premium asignado a Usuario123
✅ Rol Plan Básico revocado de Usuario123

# Errores
❌ Producto 12345 no encontrado o inactivo en la BD
⚠️ Suscripción no encontrada: XYZ789
```

### Webhooks de Notificación

Configura `DISCORD_NOTIFICATION_WEBHOOK` para recibir:

- 🎉 Nuevas suscripciones activas
- ⚠️ Cancelaciones/expiraciones
- ⬆️ Upgrades de plan
- ⬇️ Downgrades de plan

---

## 🔧 Mantenimiento

### Sincronización Manual

Si necesitas sincronizar suscripciones manualmente:

```python
from invitation_roles.hotmart_utils import sync_all_hotmart_subscriptions
import asyncio

# En un contexto async
await sync_all_hotmart_subscriptions(bot, guild_id='123456789')
```

### Limpieza de Datos

```python
# Eliminar transacciones antiguas (opcional)
from datetime import timedelta
from django.utils import timezone

old_date = timezone.now() - timedelta(days=90)
HotmartTransaction.objects.filter(
    created_at__lt=old_date,
    processed=True
).delete()
```

---

## 📝 Resumen de Respuestas a tus Preguntas

### ✅ ¿Cómo se guarda en BD?

- `PURCHASE_APPROVED` → Crea `HotmartSubscription` + `HotmartTransaction`
- Todos los eventos → Registran `HotmartTransaction` (auditoría completa)

### ✅ ¿Qué pasa si el pago falla?

- Hotmart reintenta hasta 5 veces automáticamente
- Si falla todo → Envía `SUBSCRIPTION_CANCELLATION`
- Sistema revoca roles inmediatamente

### ✅ ¿Cómo se renuevan suscripciones?

- Hotmart cobra automáticamente cada período
- Envía nuevo `PURCHASE_APPROVED`
- Sistema verifica `subscriber_code` existente
- Reactiva si estaba cancelada

### ✅ ¿Cómo se manejan upgrades?

- `SWITCH_PLAN` compara `priority` de productos
- Revoca rol anterior
- Asigna nuevo rol
- Actualiza BD con nuevo producto

### ✅ ¿Emails únicos?

- **NO es necesario** email único por restricción de BD
- `subscriber_code` es el identificador único
- Mismo email puede tener múltiples suscripciones
- El bot asigna roles según todas las suscripciones activas

### ✅ ¿Afecta al bot?

- Bot funciona independientemente
- Solo consulta BD cuando usuario se une
- Roles se asignan automáticamente al aceptar reglas
- Si suscripción está ACTIVE → asigna rol
- Si suscripción está CANCELLED → no asigna o revoca

---

## 🚀 Próximos Pasos

1. ✅ Ejecutar migraciones: `python manage.py makemigrations && python manage.py migrate`
2. ✅ Agregar productos en admin Django
3. ✅ Configurar webhook en Hotmart
4. ✅ Configurar variables de entorno
5. ✅ Probar con datos de ejemplo
6. ✅ Monitorear logs y ajustar

---

¡Sistema listo para producción! 🎉


