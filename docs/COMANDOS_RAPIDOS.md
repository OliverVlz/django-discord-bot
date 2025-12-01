# ⚡ Comandos Rápidos - Hotmart Integration

## 🚀 Instalación Inicial

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar migraciones
cd discord
python manage.py makemigrations
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Configurar productos de ejemplo (opcional)
cd ..
python setup_hotmart.py

# Iniciar servidor Django
cd discord
python manage.py runserver

# Iniciar bot Discord (en otra terminal)
cd ..
python bot.py
```

---

## 🧪 Pruebas de Webhook

### PURCHASE_APPROVED

```bash
curl -X POST http://localhost:8000/invitation_roles/hotmart/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event": "PURCHASE_APPROVED",
    "id": "test-001",
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

### SUBSCRIPTION_CANCELLATION

```bash
curl -X POST http://localhost:8000/invitation_roles/hotmart/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event": "SUBSCRIPTION_CANCELLATION",
    "id": "test-002",
    "data": {
      "subscriber": {"code": "SUB001", "email": "test@example.com"},
      "product": {"id": "0"},
      "cancellation_date": 1609181285500
    }
  }'
```

### SWITCH_PLAN

```bash
curl -X POST http://localhost:8000/invitation_roles/hotmart/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event": "SWITCH_PLAN",
    "id": "test-003",
    "data": {
      "plans": [
        {"id": 654321, "name": "Plan Premium", "current": true},
        {"id": 123456, "name": "Plan Básico", "current": false}
      ],
      "subscription": {
        "subscriber_code": "SUB001",
        "product": {"id": "0"},
        "status": "ACTIVE"
      }
    }
  }'
```

---

## 🔍 Consultas de Base de Datos

### Django Shell

```bash
cd discord
python manage.py shell
```

```python
from invitation_roles.models import HotmartProduct, HotmartSubscription, HotmartTransaction

# Ver todos los productos
HotmartProduct.objects.all()

# Ver suscripciones activas
HotmartSubscription.objects.filter(status='ACTIVE')

# Ver suscripciones por email
HotmartSubscription.objects.filter(email='user@example.com')

# Ver últimas transacciones
HotmartTransaction.objects.all().order_by('-created_at')[:10]

# Ver transacciones con errores
HotmartTransaction.objects.filter(processed=False)

# Ver detalles de una suscripción
sub = HotmartSubscription.objects.first()
print(f"Email: {sub.email}")
print(f"Producto: {sub.product.product_name}")
print(f"Estado: {sub.status}")
print(f"Member ID: {sub.member_id}")
print(f"Rol ID: {sub.current_role_id}")
```

---

## 📊 Consultas SQL Directas

```sql
-- Suscripciones activas
SELECT email, product_id, status, member_id
FROM invitation_roles_hotmartsubscription
WHERE status = 'ACTIVE';

-- Transacciones del último mes
SELECT event_type, email, status, created_at
FROM invitation_roles_hotmarttransaction
WHERE created_at > NOW() - INTERVAL '30 days'
ORDER BY created_at DESC;

-- Productos más populares
SELECT p.product_name, COUNT(s.id) as suscripciones
FROM invitation_roles_hotmartproduct p
LEFT JOIN invitation_roles_hotmartsubscription s ON p.id = s.product_id
GROUP BY p.id
ORDER BY suscripciones DESC;

-- Errores no procesados
SELECT event_type, email, error_message, created_at
FROM invitation_roles_hotmarttransaction
WHERE processed = false
ORDER BY created_at DESC;
```

---

## 🧹 Limpieza y Mantenimiento

### Eliminar transacciones antiguas (>90 días)

```python
from invitation_roles.models import HotmartTransaction
from datetime import timedelta
from django.utils import timezone

old_date = timezone.now() - timedelta(days=90)
HotmartTransaction.objects.filter(
    created_at__lt=old_date,
    processed=True
).delete()
```

### Eliminar suscripciones canceladas antiguas

```python
from invitation_roles.models import HotmartSubscription
from datetime import timedelta
from django.utils import timezone

old_date = timezone.now() - timedelta(days=180)
HotmartSubscription.objects.filter(
    status='CANCELLED',
    cancellation_date__lt=old_date
).delete()
```

---

## 🔧 Comandos de Admin

### Crear producto manualmente

```python
from invitation_roles.models import HotmartProduct

HotmartProduct.objects.create(
    product_id='12345',
    product_name='Nuevo Producto',
    discord_role_id='987654321',
    is_subscription=True,
    priority=7,
    is_active=True
)
```

### Actualizar prioridad de producto

```python
producto = HotmartProduct.objects.get(product_id='12345')
producto.priority = 10
producto.save()
```

### Cancelar suscripción manualmente

```python
from django.utils import timezone

sub = HotmartSubscription.objects.get(subscriber_code='ABC123')
sub.status = 'CANCELLED'
sub.cancellation_date = timezone.now()
sub.save()
```

### Reactivar suscripción

```python
sub = HotmartSubscription.objects.get(subscriber_code='ABC123')
sub.status = 'ACTIVE'
sub.cancellation_date = None
sub.save()
```

---

## 📈 Estadísticas Rápidas

```python
from invitation_roles.models import HotmartSubscription, HotmartTransaction
from django.db.models import Count

# Total de suscripciones activas
HotmartSubscription.objects.filter(status='ACTIVE').count()

# Total de suscripciones por estado
HotmartSubscription.objects.values('status').annotate(total=Count('id'))

# Total de transacciones por tipo de evento
HotmartTransaction.objects.values('event_type').annotate(total=Count('id'))

# Total de transacciones procesadas vs no procesadas
HotmartTransaction.objects.values('processed').annotate(total=Count('id'))

# Suscripciones vinculadas a Discord
HotmartSubscription.objects.filter(
    status='ACTIVE',
    member_id__isnull=False
).count()

# Suscripciones sin vincular
HotmartSubscription.objects.filter(
    status='ACTIVE',
    member_id__isnull=True
).count()
```

---

## 🚨 Debugging

### Ver logs del webhook

```bash
# Django
cd discord
python manage.py runserver

# Buscar en logs:
# 📩 Webhook de Hotmart recibido: [EVENT_TYPE]
# ✅ Suscripción creada: [CODE]
# ❌ Error: [MENSAJE]
```

### Ver logs del bot

```bash
python bot.py

# Buscar en logs:
# ✅ Rol asignado a [USUARIO]
# 🔄 Revocando roles para: [EMAIL]
# ⬆️ UPGRADE detectado
```

### Verificar configuraciones

```python
from invitation_roles.models import BotConfiguration

# Ver todas las configuraciones
for config in BotConfiguration.objects.filter(is_active=True):
    print(f"{config.name}: {config.value}")

# Verificar configuración específica
guild_id = BotConfiguration.objects.get(name='guild_id', is_active=True)
print(f"Guild ID: {guild_id.value}")
```

---

## 🔐 Variables de Entorno

```bash
# .env file
DISCORD_BOT_TOKEN=tu_token_aqui
RESEND_API_KEY=tu_api_key_aqui
DISCORD_NOTIFICATION_WEBHOOK=https://discord.com/api/webhooks/...

# PostgreSQL (si usas)
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Django
DJANGO_SECRET_KEY=tu_secret_key_aqui
DEBUG=True
```

---

## 📦 Backup y Restore

### Backup de la base de datos

```bash
cd discord
python manage.py dumpdata invitation_roles > backup_hotmart.json
```

### Restore

```bash
python manage.py loaddata backup_hotmart.json
```

### Backup solo productos

```bash
python manage.py dumpdata invitation_roles.HotmartProduct > backup_products.json
```

---

## 🎯 URLs Importantes

```
Admin Django: http://localhost:8000/admin/
Webhook Hotmart: http://localhost:8000/invitation_roles/hotmart/webhook/
Generate Invite: http://localhost:8000/invitation_roles/generate-invite/

# En producción:
Admin: https://tu-dominio.com/admin/
Webhook: https://tu-dominio.com/invitation_roles/hotmart/webhook/
```

---

## 🔄 Flujo de Desarrollo

```bash
# 1. Hacer cambios en models.py
nano discord/invitation_roles/models.py

# 2. Crear migración
cd discord
python manage.py makemigrations

# 3. Ver SQL de la migración (opcional)
python manage.py sqlmigrate invitation_roles 0006

# 4. Aplicar migración
python manage.py migrate

# 5. Reiniciar servidor
python manage.py runserver

# 6. Reiniciar bot (en otra terminal)
cd ..
python bot.py
```

---

## 📝 Logs y Monitoreo

### Tail logs en tiempo real (Linux/Mac)

```bash
# Django logs
cd discord
python manage.py runserver | tee django.log

# Bot logs
python bot.py | tee bot.log
```

### Ver últimas líneas de log

```bash
tail -f django.log
tail -f bot.log
```

### Buscar errores en logs

```bash
grep "❌" django.log
grep "ERROR" bot.log
```

---

## 🎉 Comandos de Producción

### Collect static files

```bash
cd discord
python manage.py collectstatic --noinput
```

### Ejecutar con Gunicorn

```bash
gunicorn discord.wsgi:application --bind 0.0.0.0:8000
```

### Ejecutar bot como servicio (systemd)

```ini
# /etc/systemd/system/discord-bot.service
[Unit]
Description=Discord Bot Hotmart
After=network.target

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/ruta/a/django-discord-bot
ExecStart=/ruta/a/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable discord-bot
sudo systemctl start discord-bot
sudo systemctl status discord-bot
```

---

¡Comandos listos para copiar y pegar! 🚀


