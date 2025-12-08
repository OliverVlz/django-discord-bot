# 🛒 Integración Hotmart - Documentación Completa

Sistema de gestión automática de roles de Discord basado en suscripciones y compras de Hotmart.

## 📋 Tabla de Contenidos

1. [Descripción General](#-descripción-general)
2. [Arquitectura](#-arquitectura)
3. [Instalación](#-instalación)
4. [Configuración](#-configuración)
5. [Eventos Soportados](#-eventos-soportados)
6. [Flujos de Trabajo](#-flujos-de-trabajo)
7. [Modelos de Base de Datos](#-modelos-de-base-de-datos)
8. [Troubleshooting](#-troubleshooting)

---

## 🎯 Descripción General

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

## 🏗️ Arquitectura

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

## 🚀 Instalación

### 1. Instalar Dependencias

```bash
pip install -r requirements.txt
```

Nueva dependencia: `python-dateutil==2.9.0`

### 2. Ejecutar Migraciones

```bash
cd discord
python manage.py makemigrations
python manage.py migrate
```

Esto creará las siguientes tablas:
- `HotmartProduct` → Productos de Hotmart vinculados a roles de Discord
- `HotmartSubscription` → Suscripciones activas de usuarios
- `HotmartTransaction` → Registro de todos los eventos recibidos

### 3. Variables de Entorno

```env
# Discord
DISCORD_BOT_TOKEN=tu_token_del_bot
DISCORD_NOTIFICATION_WEBHOOK=https://discord.com/api/webhooks/...  # Opcional

# Email (Gmail)
GMAIL_ADDRESS=tu-email@gmail.com
GMAIL_APP_PASSWORD=tu-app-password
```

**Configurar Gmail App Password:**

1. Ve a tu cuenta de Google: [myaccount.google.com](https://myaccount.google.com)
2. Activa la **verificación en dos pasos** (requerida para app passwords)
3. Ve a **Seguridad** → **Contraseñas de aplicaciones**
4. Selecciona **Correo** y **Otro (personalizado)** → Escribe "Discord Bot"
5. Copia la contraseña generada (16 caracteres sin espacios)
6. Úsala como `GMAIL_APP_PASSWORD` en las variables de entorno

---

## ⚙️ Configuración

### 1. Configurar Productos en el Admin

Ir a: **Invitation Roles → Hotmart Products → Add**

**Ejemplo de configuración:**

| Campo           | Valor                | Descripción                    |
| --------------- | -------------------- | ------------------------------ |
| Product ID      | `788921`             | ID del producto en Hotmart     |
| Product name    | `Curso Premium IMAX` | Nombre descriptivo             |
| Discord role ID | `1234567890`         | ID del rol en Discord          |
| Is subscription | ✅                   | Si es suscripción recurrente   |
| Is active       | ✅                   | Si está activo                 |
| Priority        | `10`                 | Prioridad (mayor = mejor plan) |

**Productos de ejemplo:**

```python
# Plan Básico
Product ID: 0
Product name: Curso Básico IMAX
Discord role ID: TU_ROLE_ID_BASICO
Is subscription: ✅
Priority: 5
Is active: ✅

# Plan Premium
Product ID: 788921
Product name: Curso Premium IMAX
Discord role ID: TU_ROLE_ID_PREMIUM
Is subscription: ✅
Priority: 10
Is active: ✅
```

### 2. Configurar Bot Configuration

Ir a: **Invitation Roles → Bot Configurations**

Asegúrate de que existan estas configuraciones:

| Name                 | Value        | Type    | Description                        |
| -------------------- | ------------ | ------- | ---------------------------------- |
| `guild_id`           | `1234567890` | guild   | ID del servidor Discord            |
| `welcome_channel_id` | `1234567890` | channel | Canal de bienvenida                |
| `rules_channel_id`   | `1234567890` | channel | Canal de reglas                    |
| `invite_ttl_seconds` | `604800`     | general | Tiempo de vida del invite (7 días) |
| `visitor_role_id`    | `1234567890` | general | Rol visitante (opcional)           |

### 3. Configurar Webhook en Hotmart

**URL del Webhook:**

```
https://tu-dominio.com/invitation_roles/hotmart/webhook/
```

**Eventos a Escuchar:**

- ✅ `PURCHASE_APPROVED`
- ✅ `PURCHASE_COMPLETE`
- ✅ `PURCHASE_REFUNDED`
- ✅ `PURCHASE_PROTEST`
- ✅ `SUBSCRIPTION_CANCELLATION`
- ✅ `SWITCH_PLAN`
- ✅ `UPDATE_SUBSCRIPTION_CHARGE_DATE`

---

## 📨 Eventos Soportados

### 1. PURCHASE_APPROVED (Compra Aprobada)

**¿Cuándo ocurre?** Cuando se aprueba un pago.

**Acciones:**
1. ✅ Verifica que el producto existe en BD
2. ✅ Crea o reactiva la suscripción
3. ✅ Registra la transacción
4. ✅ Genera invite único de Discord (si no tiene `member_id`)
5. ✅ Envía correo con link de invitación (si no tiene `member_id`)
6. ✅ Asigna rol directamente si tiene `member_id` registrado

**Resultado:** Usuario recibe acceso inmediato.

### 2. PURCHASE_COMPLETE (Compra Completada)

**¿Cuándo ocurre?** Cuando expira el período de garantía.

**Acciones:**
1. ✅ Registra la transacción como COMPLETED
2. ℹ️ Solo informativo, no afecta acceso

**Resultado:** La compra ya no puede reembolsarse.

### 3. PURCHASE_REFUNDED (Reembolso)

**¿Cuándo ocurre?** Cuando se devuelve el dinero al comprador.

**Acciones:**
1. ✅ Marca la suscripción como CANCELLED
2. ✅ Revoca roles de Discord
3. ✅ Asigna rol visitante (si está configurado)
4. ✅ Registra la transacción

**Resultado:** Usuario pierde acceso inmediatamente.

### 4. SUBSCRIPTION_CANCELLATION (Cancelación)

**¿Cuándo ocurre?** Cuando el usuario o sistema cancela la suscripción.

**Acciones:**
1. ✅ Busca la suscripción por `subscriber_code`
2. ✅ Marca como CANCELLED
3. ✅ Revoca roles de Discord
4. ✅ Asigna rol visitante (si está configurado)
5. ✅ Registra fecha de cancelación

**Resultado:** Usuario pierde acceso.

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

**Resultado:** Usuario obtiene roles correspondientes al nuevo plan.

### 6. UPDATE_SUBSCRIPTION_CHARGE_DATE

**¿Cuándo ocurre?** Cuando cambia la fecha de próximo cobro.

**Acciones:**
1. ✅ Actualiza `next_charge_date` en suscripción
2. ℹ️ Solo informativo

**Resultado:** BD actualizada con nueva fecha.

### 7. PURCHASE_PROTEST (Disputa)

**¿Cuándo ocurre?** Cuando hay una disputa de pago.

**Acciones:**
1. ✅ Suspende suscripción (estado `SUSPENDED`)
2. ⚠️ NO revoca roles (mantiene acceso durante investigación)

**Resultado:** Suscripción suspendida, acceso temporal.

---

## 🔄 Flujos de Trabajo

### Flujo 1: Nueva Compra

```
1. Usuario compra en Hotmart
   ↓
2. Hotmart envía PURCHASE_APPROVED
   ↓
3. Django crea suscripción (status=ACTIVE)
   ↓
4. Django genera invite único de Discord
   ↓
5. Django envía email con link de invite
   ↓
6. Usuario recibe email y hace click
   ↓
7. Usuario se une al servidor Discord
   ↓
8. Bot detecta entrada y marca invite como PENDING_VERIFICATION
   ↓
9. Usuario lee reglas y hace click en "Acepto las Reglas"
   ↓
10. Bot asigna rol según producto
   ↓
11. Bot actualiza suscripción con member_id y role_id
   ↓
12. ✅ Usuario tiene acceso completo
```

### Flujo 2: Renovación Mensual

```
1. Mes siguiente, Hotmart cobra automáticamente
   ↓
2. Hotmart envía PURCHASE_APPROVED (nuevo cobro)
   ↓
3. Sistema busca suscripción existente por subscriber_code
   ↓
4. Reactiva si estaba cancelada
   ↓
5. Actualiza next_charge_date
   ↓
6. Usuario mantiene acceso
```

### Flujo 3: Fallo en Renovación

```
1. Tarjeta rechazada
   ↓
2. Hotmart reintenta hasta 5 veces
   ↓
3. Si falla todo, cancela automáticamente
   ↓
4. Hotmart envía SUBSCRIPTION_CANCELLATION
   ↓
5. Sistema marca como CANCELLED
   ↓
6. Revoca roles de Discord
   ↓
7. Asigna rol visitante (si está configurado)
   ↓
8. Usuario pierde acceso
```

### Flujo 4: Upgrade de Plan

```
1. Usuario en "Plan Básico" (priority=5)
   ↓
2. Compra "Plan Premium" (priority=10)
   ↓
3. Hotmart envía SWITCH_PLAN
   ↓
4. Sistema detecta upgrade (10 > 5)
   ↓
5. Revoca rol "Plan Básico"
   ↓
6. Asigna rol "Plan Premium"
   ↓
7. Actualiza BD
```

---

## 🗄️ Modelos de Base de Datos

### HotmartProduct

Productos de Hotmart → Roles de Discord

```python
{
    'product_id': '788921',
    'product_name': 'Curso Premium',
    'discord_role_id': '123456789',
    'is_subscription': True,
    'priority': 10,
    'is_active': True
}
```

**Campos clave:**
- `priority`: Determina jerarquía en upgrades/downgrades
  - `priority = 10` → Plan Premium
  - `priority = 5` → Plan Básico
  - `priority = 1` → Plan Gratuito

### HotmartSubscription

Suscripciones activas de usuarios

```python
{
    'subscriber_code': 'ABC123',  # IDENTIFICADOR ÚNICO
    'email': 'user@example.com',
    'product': <HotmartProduct>,
    'status': 'ACTIVE',
    'member_id': '987654321',
    'current_role_id': '123456789',
    'next_charge_date': '2025-10-30'
}
```

**Estados posibles:**
- `ACTIVE` → Suscripción activa, tiene acceso
- `CANCELLED` → Cancelada, sin acceso
- `SUSPENDED` → Suspendida (por disputa), sin acceso
- `EXPIRED` → Expirada, sin acceso
- `PENDING_PAYMENT` → Pago pendiente, acceso temporal

### HotmartTransaction

Registro de todos los eventos recibidos para auditoría

```python
{
    'hotmart_event_id': 'abc-123-def',
    'event_type': 'PURCHASE_APPROVED',
    'email': 'user@example.com',
    'status': 'APPROVED',
    'processed': True,
    'raw_webhook_data': {...}  # JSON completo
}
```

---

## 🧪 Pruebas

### Probar Webhook Localmente

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

### Verificar en el Admin

1. Ir a **Hotmart Transactions**
2. Deberías ver la transacción de prueba
3. Ir a **Hotmart Subscriptions**
4. Deberías ver la suscripción creada

---

## 🔧 Troubleshooting

### Producto No Encontrado

```
❌ Producto 12345 no encontrado o inactivo en la BD
```

**Solución:**
1. Verifica que el `product_id` en Hotmart coincida con el de tu BD
2. Verifica que el producto esté marcado como `is_active = True`
3. Añade el producto en el admin si no existe

### No se Envía el Correo

```
❌ Error enviando correo de invitación
```

**Solución:**
1. Verifica que `GMAIL_ADDRESS` y `GMAIL_APP_PASSWORD` estén configuradas
2. Verifica que hayas creado una "App Password" en tu cuenta de Google
3. Asegúrate de que la verificación en dos pasos esté activada en tu cuenta de Google

### No se Asignan Roles

```
❌ No se puede asignar el rol. El rol del bot es igual o inferior
```

**Solución:**
1. En Discord, mueve el rol del bot **por encima** de los roles que debe asignar
2. Verifica que el bot tenga el permiso "Gestionar Roles"

### Evento Duplicado

```
⚠️ Evento duplicado ignorado: abc-123-def
```

**Solución:**
- Esto es normal, Hotmart a veces reenvía eventos
- El sistema ignora automáticamente eventos ya procesados
- No requiere acción

### Usuario con Email Duplicado

**Problema:** Mismo email intenta comprar dos veces

**Solución:**
- `subscriber_code` es ÚNICO por suscripción
- `email` se repite pero cada suscripción es independiente
- Sistema busca primero por `subscriber_code`
- Si es renovación, actualiza la existente
- Si es nuevo producto, crea nueva suscripción

---

## 📊 Monitoreo

### Ver Suscripciones Activas

**Admin Django:**
```
http://localhost:8000/admin/invitation_roles/hotmartsubscription/
```

Filtra por:
- `status = ACTIVE` → Suscripciones activas
- `status = CANCELLED` → Canceladas
- `member_id (vacío)` → Sin Discord asignado

### Ver Transacciones con Errores

```
http://localhost:8000/admin/invitation_roles/hotmarttransaction/
```

Filtra por:
- `processed = False` → Eventos con errores
- Revisa `error_message` para ver qué falló

### Logs del Bot

```bash
# Bot logs
✅ Rol Plan Premium asignado a Usuario123
🔄 Revocando roles para: user@example.com
⬆️ UPGRADE detectado: Plan Básico → Plan Premium
```

---

## 📝 Checklist de Configuración

Antes de poner en producción:

- [ ] Migraciones ejecutadas correctamente
- [ ] Productos configurados en admin con IDs de roles reales
- [ ] Bot configurations configuradas (guild_id, channels, etc.)
- [ ] Variables de entorno configuradas (DISCORD_BOT_TOKEN, GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
- [ ] Webhook configurado en Hotmart apuntando a tu servidor
- [ ] Probado con evento de prueba (PURCHASE_APPROVED)
- [ ] Bot de Discord iniciado y respondiendo
- [ ] Roles de Discord configurados con jerarquía correcta
- [ ] Sistema de notificaciones configurado (opcional)
- [ ] Backups de base de datos configurados

---

**Última actualización**: Enero 2025  
**Versión**: 2.0.0

