# 📊 Diagramas de Flujo - Integración Hotmart

## 🎯 Flujo General del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                         USUARIO COMPRA                           │
│                     Producto en Hotmart                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   HOTMART PROCESA PAGO                           │
│            (Tarjeta, PayPal, PIX, etc.)                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              HOTMART ENVÍA WEBHOOK                               │
│        POST /invitation_roles/hotmart/webhook/                   │
│        Event: PURCHASE_APPROVED                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              DJANGO RECIBE WEBHOOK                               │
│   1. Valida estructura del JSON                                 │
│   2. Verifica que no sea duplicado (event_id)                   │
│   3. Extrae datos del webhook                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           BUSCA PRODUCTO EN BASE DE DATOS                        │
│   ¿Existe product_id en HotmartProduct?                         │
└────────────┬───────────────────────────┬────────────────────────┘
             │ NO                         │ SÍ
             ▼                            ▼
    ┌────────────────┐         ┌──────────────────────┐
    │ REGISTRA ERROR │         │ CREA/ACTUALIZA       │
    │ processed=False│         │ SUSCRIPCIÓN          │
    │ Fin            │         │ status=ACTIVE        │
    └────────────────┘         └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │ REGISTRA TRANSACCIÓN │
                               │ processed=True       │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │ GENERA INVITE ÚNICO  │
                               │ Discord (1 uso)      │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │ ENVÍA EMAIL          │
                               │ con link Discord     │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │ USUARIO RECIBE EMAIL │
                               │ Click en link        │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │ SE UNE AL SERVIDOR   │
                               │ Discord              │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │ BOT DETECTA ENTRADA  │
                               │ Busca por invite_code│
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │ MARCA INVITE COMO    │
                               │ PENDING_VERIFICATION │
                               │ Guarda member_id     │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │ USUARIO LEE REGLAS   │
                               │ Click "Acepto"       │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │ BOT ASIGNA ROL       │
                               │ según product        │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │ ACTUALIZA SUSCRIPCIÓN│
                               │ member_id + role_id  │
                               │ last_sync_at = now   │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │ ✅ USUARIO ACTIVO    │
                               │ Acceso completo      │
                               └──────────────────────┘
```

---

## 🔄 Flujo de Renovación Mensual

```
┌──────────────────────┐
│ MES 1: COMPRA INICIAL│
│ PURCHASE_APPROVED    │
│ Suscripción creada   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Usuario tiene acceso │
│ status = ACTIVE      │
│ next_charge_date Set │
└──────────┬───────────┘
           │
           │ (30 días después)
           ▼
┌──────────────────────┐
│ MES 2: HOTMART COBRA │
│ Automáticamente      │
└──────────┬───────────┘
           │
           ├─────────────────────┐
           │                     │
    ✅ PAGO OK          ❌ PAGO FALLA
           │                     │
           ▼                     ▼
┌──────────────────────┐  ┌──────────────────┐
│ PURCHASE_APPROVED    │  │ Hotmart reintenta│
│ (renovación)         │  │ 5 veces          │
└──────────┬───────────┘  └────────┬─────────┘
           │                       │
           │                       ▼
           │              ┌─────────────────┐
           │              │ Todos fallan?   │
           │              └────────┬────────┘
           │                       │
           │                       ▼
           │              ┌─────────────────┐
           │              │ SUBSCRIPTION_   │
           │              │ CANCELLATION    │
           │              └────────┬────────┘
           │                       │
           ▼                       ▼
┌──────────────────────┐  ┌─────────────────┐
│ Actualiza next_charge│  │ status=CANCELLED│
│ Usuario sigue activo │  │ Revoca roles    │
└──────────────────────┘  │ Usuario pierde  │
                          │ acceso          │
                          └─────────────────┘
```

---

## ⬆️ Flujo de Upgrade

```
┌─────────────────────────────────────────────┐
│ ESTADO INICIAL                              │
│ Usuario: Plan Básico (priority=5)          │
│ Rol Discord: "Plan Básico"                 │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Usuario compra Plan Premium en Hotmart      │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Hotmart envía SWITCH_PLAN                   │
│ plans: [                                    │
│   {id: 654321, name: "Premium", current: T} │
│   {id: 123456, name: "Básico", current: F}  │
│ ]                                           │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Django busca suscripción por subscriber_code│
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Compara prioridades:                        │
│ Plan Premium (priority=10) > Básico (5)     │
│ → UPGRADE detectado ⬆️                      │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ 1. Revoca rol "Plan Básico"                │
│    bot.remove_roles(member, role_basico)    │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ 2. Actualiza suscripción en BD              │
│    subscription.product = plan_premium      │
│    subscription.plan_id = 654321            │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ 3. Asigna rol "Plan Premium"                │
│    bot.add_roles(member, role_premium)      │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ 4. Registra transacción                     │
│    event_type = SWITCH_PLAN                 │
│    processed = True                         │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ ✅ UPGRADE COMPLETADO                       │
│ Usuario: Plan Premium (priority=10)         │
│ Rol Discord: "Plan Premium"                 │
└─────────────────────────────────────────────┘
```

---

## 💳 Flujo de Reembolso

```
┌─────────────────────────────────────────────┐
│ Usuario solicita reembolso en Hotmart       │
│ (dentro del período de garantía)            │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Hotmart aprueba reembolso                   │
│ Devuelve dinero al cliente                  │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Hotmart envía PURCHASE_REFUNDED             │
│ status: REFUNDED                            │
│ subscriber_code: ABC123                     │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Django busca suscripción                    │
│ HotmartSubscription.get(subscriber_code)    │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Actualiza suscripción                       │
│ status = CANCELLED                          │
│ cancellation_date = now()                   │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Revoca roles de Discord                     │
│ if subscription.member_id:                  │
│   bot.remove_roles(member, role)            │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Registra transacción                        │
│ event_type = PURCHASE_REFUNDED              │
│ status = REFUNDED                           │
│ processed = True                            │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ ✅ REEMBOLSO PROCESADO                      │
│ Usuario perdió acceso al servidor           │
│ Suscripción marcada como CANCELLED          │
└─────────────────────────────────────────────┘
```

---

## 🔍 Flujo de Verificación de Email Único

```
┌─────────────────────────────────────────────┐
│ Webhook recibido con email "user@test.com" │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ ¿Qué identificador usar?                    │
│                                             │
│ ❌ NO: email (puede repetirse)              │
│ ✅ SÍ: subscriber_code (ÚNICO)              │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Buscar suscripción por subscriber_code      │
│ HotmartSubscription.get(subscriber_code)    │
└────────┬───────────────────┬────────────────┘
         │ EXISTE            │ NO EXISTE
         ▼                   ▼
┌────────────────┐  ┌──────────────────────┐
│ ES RENOVACIÓN  │  │ ES PRIMERA COMPRA    │
│ O REACTIVACIÓN │  │ O NUEVO PRODUCTO     │
└────────┬───────┘  └──────────┬───────────┘
         │                     │
         ▼                     ▼
┌────────────────┐  ┌──────────────────────┐
│ Reactiva       │  │ Crea nueva           │
│ status=ACTIVE  │  │ suscripción          │
└────────┬───────┘  └──────────┬───────────┘
         │                     │
         └─────────┬───────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ ¿Mismo usuario con múltiples suscripciones? │
│                                             │
│ SÍ es posible:                              │
│ Suscripción 1: subscriber_code = ABC123     │
│               email = user@test.com         │
│               product = Plan Básico         │
│                                             │
│ Suscripción 2: subscriber_code = XYZ789     │
│               email = user@test.com         │
│               product = Plan Premium        │
│                                             │
│ → Ambas son independientes                  │
│ → Usuario puede tener ambos roles           │
└─────────────────────────────────────────────┘
```

---

## 🤖 Flujo del Bot de Discord

```
┌─────────────────────────────────────────────┐
│ Usuario se une al servidor Discord          │
│ (usando invite generado por webhook)        │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Bot detecta on_member_join                  │
│ Identifica invite_code usado                │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Busca invite en BD                          │
│ Invite.objects.get(invite_code=code)        │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Actualiza invite                            │
│ status = PENDING_VERIFICATION               │
│ member_id = str(member.id)                  │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Envía mensaje de bienvenida                 │
│ "Por favor acepta las reglas"               │
└────────────────────┬────────────────────────┘
                     │
                     │ (Usuario lee reglas)
                     ▼
┌─────────────────────────────────────────────┐
│ Usuario hace click en "Acepto las Reglas"   │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Bot busca invite PENDING_VERIFICATION       │
│ por member_id                               │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Obtiene role_id del invite                  │
│ role = guild.get_role(int(role_id))         │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Asigna rol al miembro                       │
│ await member.add_roles(role)                │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Actualiza invite                            │
│ status = USED                               │
│ used_at = timezone.now()                    │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Actualiza suscripción (si existe)           │
│ HotmartSubscription.update(                 │
│   member_id = member.id,                    │
│   current_role_id = role.id                 │
│ )                                           │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ ✅ PROCESO COMPLETADO                       │
│ Usuario tiene acceso completo               │
└─────────────────────────────────────────────┘
```

---

## 📊 Resumen de Estados

### Estados de Suscripción

| Estado            | Descripción                       | Tiene Acceso | Acción del Bot                    |
| ----------------- | --------------------------------- | ------------ | --------------------------------- |
| `ACTIVE`          | Suscripción activa y pagada       | ✅ SÍ        | Asignar rol                       |
| `CANCELLED`       | Cancelada por usuario o reembolso | ❌ NO        | Revocar rol                       |
| `SUSPENDED`       | Suspendida por disputa            | ❌ NO        | Revocar rol                       |
| `EXPIRED`         | Expirada por falta de pago        | ❌ NO        | Revocar rol                       |
| `PENDING_PAYMENT` | Pago pendiente                    | ⚠️ Temporal  | Mantener o revocar según política |

### Estados de Invite

| Estado                 | Descripción                           | Puede Usarse  |
| ---------------------- | ------------------------------------- | ------------- |
| `PENDING`              | Generado, esperando uso               | ✅ SÍ         |
| `PENDING_VERIFICATION` | Usado, esperando aceptación de reglas | ⏳ En proceso |
| `USED`                 | Completamente usado                   | ❌ NO         |
| `EXPIRED`              | Caducado por tiempo                   | ❌ NO         |

### Prioridades de Productos

| Priority | Ejemplo         | Uso            |
| -------- | --------------- | -------------- |
| `10`     | Plan Premium    | Nivel más alto |
| `5`      | Plan Básico     | Nivel medio    |
| `1`      | Plan Gratuito   | Nivel básico   |
| `0`      | Acceso limitado | Nivel mínimo   |

**Lógica:**

- `new_priority > old_priority` → **UPGRADE** ⬆️
- `new_priority < old_priority` → **DOWNGRADE** ⬇️
- `new_priority == old_priority` → **CAMBIO LATERAL** ↔️

---

## 🎯 Puntos Clave del Sistema

1. **Email NO es único** → Mismo email puede tener múltiples suscripciones
2. **subscriber_code ES único** → Identificador principal
3. **Upgrade/Downgrade** → Se compara `priority` de productos
4. **Revocación automática** → Al cancelar, reembolsar o expirar
5. **Auditoría completa** → Todos los eventos se guardan en `HotmartTransaction`
6. **Eventos idempotentes** → Duplicados se ignoran automáticamente
7. **Sincronización bot-BD** → `member_id` + `current_role_id` se actualizan

---

¡Sistema diseñado para escalar y manejar miles de usuarios! 🚀


