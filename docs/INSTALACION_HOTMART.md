# 🚀 Instalación Rápida - Integración Hotmart

## 📦 Paso 1: Instalar Dependencias

```bash
pip install -r requirements.txt
```

Nueva dependencia añadida: `python-dateutil==2.9.0`

---

## 🗄️ Paso 2: Ejecutar Migraciones

```bash
cd discord
python manage.py makemigrations
python manage.py migrate
```

Esto creará las siguientes tablas:

- `HotmartProduct` → Productos de Hotmart vinculados a roles de Discord
- `HotmartSubscription` → Suscripciones activas de usuarios
- `HotmartTransaction` → Registro de todos los eventos recibidos

---

## ⚙️ Paso 3: Configurar Variables de Entorno

Añade al archivo `.env` o configura en tu sistema:

```bash
# Discord
DISCORD_BOT_TOKEN=tu_token_del_bot
DISCORD_NOTIFICATION_WEBHOOK=https://discord.com/api/webhooks/...  # Opcional

# Email (Resend)
RESEND_API_KEY=tu_api_key_de_resend
```

---

## 🎯 Paso 4: Configurar Productos en el Admin

### 4.1 Crear Superusuario (si no existe)

```bash
python manage.py createsuperuser
```

### 4.2 Acceder al Admin

```
http://localhost:8000/admin/
```

### 4.3 Añadir Productos Hotmart

Ir a: **Invitation Roles → Hotmart Products → Add**

**Ejemplo de configuración:**

| Campo           | Valor                | Descripción                    |
| --------------- | -------------------- | ------------------------------ |
| Product ID      | `0` o `788921`       | ID del producto en Hotmart     |
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

---

## 🔧 Paso 5: Configurar Bot Configuration (si no existe)

Ir a: **Invitation Roles → Bot Configurations**

Asegúrate de que existan estas configuraciones:

| Name                 | Value        | Type    | Description                        |
| -------------------- | ------------ | ------- | ---------------------------------- |
| `guild_id`           | `1234567890` | guild   | ID del servidor Discord            |
| `welcome_channel_id` | `1234567890` | channel | Canal de bienvenida                |
| `rules_channel_id`   | `1234567890` | channel | Canal de reglas                    |
| `invite_ttl_seconds` | `604800`     | general | Tiempo de vida del invite (7 días) |

---

## 🌐 Paso 6: Configurar Webhook en Hotmart

### 6.1 URL del Webhook

```
https://tu-dominio.com/invitation_roles/hotmart/webhook/
```

### 6.2 Eventos a Escuchar

Marca todos estos eventos en Hotmart:

- ✅ `PURCHASE_APPROVED`
- ✅ `PURCHASE_COMPLETE`
- ✅ `PURCHASE_REFUNDED`
- ✅ `PURCHASE_PROTEST`
- ✅ `SUBSCRIPTION_CANCELLATION`
- ✅ `SWITCH_PLAN`
- ✅ `UPDATE_SUBSCRIPTION_CHARGE_DATE`

### 6.3 Configuración de Seguridad

Hotmart NO requiere token de autenticación en el webhook por defecto, pero puedes:

- Usar HTTPS (recomendado)
- Validar IPs de Hotmart (opcional)
- Verificar estructura del payload

---

## 🧪 Paso 7: Probar la Integración

### 7.1 Probar con datos de ejemplo

Usa los datos del archivo `hotmart.md`:

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

### 7.2 Verificar en el Admin

1. Ir a **Hotmart Transactions**
2. Deberías ver la transacción de prueba
3. Ir a **Hotmart Subscriptions**
4. Deberías ver la suscripción creada

### 7.3 Verificar Logs

```bash
# Django logs
python manage.py runserver

# Deberías ver:
📩 Webhook de Hotmart recibido: PURCHASE_APPROVED
✅ Suscripción creada: SUB001
✅ Invite creado: XXXX para test@example.com
✅ Correo de invitación enviado a test@example.com
```

---

## 🤖 Paso 8: Iniciar el Bot de Discord

```bash
cd ..  # Volver a la raíz del proyecto
python bot.py
```

El bot ahora:

- ✅ Procesa invites normales (como antes)
- ✅ Asigna roles cuando usuarios de Hotmart se unen
- ✅ Sincroniza estados de suscripciones

---

## 📊 Paso 9: Monitoreo

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

## 🔍 Troubleshooting

### Problema: Producto no encontrado

```
❌ Producto 12345 no encontrado o inactivo en la BD
```

**Solución:**

1. Verifica que el `product_id` en Hotmart coincida con el de tu BD
2. Verifica que el producto esté marcado como `is_active = True`
3. Añade el producto en el admin si no existe

---

### Problema: No se envía el correo

```
❌ Error enviando correo de invitación
```

**Solución:**

1. Verifica que `RESEND_API_KEY` esté configurada
2. Verifica que el dominio esté verificado en Resend
3. Cambia el remitente de `"Acme <onboarding@resend.dev>"` a tu dominio

---

### Problema: No se asignan roles

```
❌ No se puede asignar el rol. El rol del bot es igual o inferior
```

**Solución:**

1. En Discord, mueve el rol del bot **por encima** de los roles que debe asignar
2. Verifica que el bot tenga el permiso "Gestionar Roles"

---

### Problema: Evento duplicado

```
⚠️ Evento duplicado ignorado: abc-123-def
```

**Solución:**

- Esto es normal, Hotmart a veces reenvía eventos
- El sistema ignora automáticamente eventos ya procesados
- No requiere acción

---

## 📝 Checklist Final

Antes de poner en producción:

- [ ] Migraciones ejecutadas correctamente
- [ ] Productos configurados en admin con IDs de roles reales
- [ ] Bot configurations configuradas (guild_id, channels, etc.)
- [ ] Variables de entorno configuradas (DISCORD_BOT_TOKEN, RESEND_API_KEY)
- [ ] Webhook configurado en Hotmart apuntando a tu servidor
- [ ] Probado con evento de prueba (PURCHASE_APPROVED)
- [ ] Bot de Discord iniciado y respondiendo
- [ ] Roles de Discord configurados con jerarquía correcta
- [ ] Sistema de notificaciones configurado (opcional)
- [ ] Backups de base de datos configurados

---

## 🎉 ¡Listo!

Tu sistema Hotmart-Discord está configurado y funcionando.

**Próximos pasos recomendados:**

1. 📖 Leer `HOTMART_INTEGRATION.md` para entender flujos completos
2. 🧪 Hacer pruebas con usuarios reales en ambiente de pruebas
3. 📊 Monitorear logs durante las primeras semanas
4. 🔧 Ajustar prioridades de productos según necesidad
5. 📧 Personalizar emails de invitación con tu branding

---

## 📞 Soporte

Si encuentras algún problema:

1. Revisa los logs de Django y del bot
2. Verifica las transacciones en el admin con `processed=False`
3. Consulta la documentación completa en `HOTMART_INTEGRATION.md`


