from django.db import models
from django.core.exceptions import ValidationError
from uuid import uuid4

# Create your models here.

class Invite(models.Model):
    INVITE_STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('PENDING_VERIFICATION', 'Pendiente de Verificación'),
        ('USED', 'Usado'),
        ('EXPIRED', 'Expirado'),
    ]

    invite_code = models.CharField(max_length=20, unique=True, db_index=True)
    role_id = models.CharField(max_length=100) # ID del rol de Discord
    email = models.EmailField(max_length=255)
    status = models.CharField(max_length=25, choices=INVITE_STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    member_id = models.CharField(max_length=100, null=True, blank=True) # ID del miembro de Discord
    rule_message_id = models.CharField(max_length=100, null=True, blank=True) # ID del mensaje de reglas
    rule_channel_id = models.CharField(max_length=100, null=True, blank=True) # ID del canal de reglas

    def __str__(self):
        return f"{self.email} - {self.invite_code} ({self.status})"

    class Meta:
        ordering = ['created_at']


class AccessRole(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Nombre descriptivo del rol (ej: 'Nivel 1', 'VIP', 'Staff')")
    role_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="ID del rol de Discord")
    description = models.TextField(blank=True, help_text="Descripción opcional del rol y sus permisos")
    is_active = models.BooleanField(default=True, help_text="Si está activo, se incluirá en las verificaciones de acceso")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        status = "✅" if self.is_active else "❌"
        return f"{status} {self.name} (ID: {self.role_id})"

    class Meta:
        ordering = ['name']
        verbose_name = "Rol de Acceso"
        verbose_name_plural = "Roles de Acceso"


class BotConfiguration(models.Model):
    CONFIGURATION_TYPES = [
        ('guild', 'Guild/Servidor'),
        ('channel', 'Canal'),
        ('message', 'Mensaje'),
        ('category', 'Categoría'),
        ('general', 'General'),
    ]

    name = models.CharField(max_length=100, unique=True, help_text="Nombre identificativo de la configuración (ej: 'guild_id', 'rules_channel')")
    value = models.CharField(max_length=200, blank=True, help_text="Valor de la configuración (ID de Discord, número, etc.)")
    configuration_type = models.CharField(max_length=20, choices=CONFIGURATION_TYPES, help_text="Tipo de configuración")
    description = models.TextField(blank=True, help_text="Descripción de para qué se usa esta configuración")
    is_active = models.BooleanField(default=True, help_text="Si está activa, el bot la usará")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.is_active:
            existing = BotConfiguration.objects.filter(name=self.name, is_active=True).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError(f"Ya existe una configuración activa con el nombre '{self.name}'")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        status = "✅" if self.is_active else "❌"
        return f"{status} {self.name}: {self.value}"

    class Meta:
        ordering = ['configuration_type', 'name']
        verbose_name = "Configuración del Bot"
        verbose_name_plural = "Configuraciones del Bot"


class HotmartProduct(models.Model):
    product_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="ID del producto en Hotmart")
    product_name = models.CharField(max_length=255, help_text="Nombre del producto")
    discord_role_id = models.CharField(max_length=100, help_text="ID del rol de Discord a asignar")
    is_subscription = models.BooleanField(default=True, help_text="Si es un producto de suscripción recurrente")
    is_active = models.BooleanField(default=True, help_text="Si el producto está activo")
    priority = models.IntegerField(default=0, help_text="Prioridad del producto (mayor = mejor plan)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        status = "✅" if self.is_active else "❌"
        tipo = "Suscripción" if self.is_subscription else "Pago único"
        return f"{status} {self.product_name} ({tipo}) - Prioridad: {self.priority}"

    class Meta:
        ordering = ['-priority', 'product_name']
        verbose_name = "Producto Hotmart"
        verbose_name_plural = "Productos Hotmart"


class HotmartSubscription(models.Model):
    SUBSCRIPTION_STATUS_CHOICES = [
        ('ACTIVE', 'Activa'),
        ('CANCELLED', 'Cancelada'),
        ('SUSPENDED', 'Suspendida'),
        ('EXPIRED', 'Expirada'),
        ('PENDING_PAYMENT', 'Pendiente de Pago'),
    ]

    subscriber_code = models.CharField(max_length=100, unique=True, db_index=True, help_text="Código único del suscriptor en Hotmart")
    email = models.EmailField(max_length=255, db_index=True, help_text="Email del suscriptor")
    product = models.ForeignKey(HotmartProduct, on_delete=models.CASCADE, related_name='subscriptions')
    plan_id = models.CharField(max_length=100, help_text="ID del plan de suscripción")
    plan_name = models.CharField(max_length=255, help_text="Nombre del plan")
    
    status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS_CHOICES, default='ACTIVE')
    
    member_id = models.CharField(max_length=100, null=True, blank=True, db_index=True, help_text="ID del miembro en Discord")
    current_role_id = models.CharField(max_length=100, null=True, blank=True, help_text="Rol actual asignado")
    
    next_charge_date = models.DateTimeField(null=True, blank=True, help_text="Fecha del próximo cobro")
    cancellation_date = models.DateTimeField(null=True, blank=True, help_text="Fecha de cancelación")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync_at = models.DateTimeField(null=True, blank=True, help_text="Última sincronización con Discord")

    def __str__(self):
        return f"{self.email} - {self.product.product_name} ({self.status})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Suscripción Hotmart"
        verbose_name_plural = "Suscripciones Hotmart"
        indexes = [
            models.Index(fields=['email', 'status']),
            models.Index(fields=['subscriber_code', 'status']),
        ]


class HotmartTransaction(models.Model):
    TRANSACTION_STATUS_CHOICES = [
        ('APPROVED', 'Aprobada'),
        ('COMPLETED', 'Completada'),
        ('REFUNDED', 'Reembolsada'),
        ('DISPUTE', 'Disputa'),
        ('CANCELLED', 'Cancelada'),
        ('PENDING', 'Pendiente'),
    ]

    EVENT_TYPE_CHOICES = [
        ('PURCHASE_APPROVED', 'Compra Aprobada'),
        ('PURCHASE_COMPLETE', 'Compra Completada'),
        ('PURCHASE_REFUNDED', 'Compra Reembolsada'),
        ('PURCHASE_PROTEST', 'Disputa de Compra'),
        ('SUBSCRIPTION_CANCELLATION', 'Cancelación de Suscripción'),
        ('SWITCH_PLAN', 'Cambio de Plan'),
        ('UPDATE_SUBSCRIPTION_CHARGE_DATE', 'Actualización de Fecha de Cobro'),
    ]

    transaction_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="ID único de la transacción")
    hotmart_event_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="ID del evento de Hotmart")
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES, help_text="Tipo de evento de Hotmart")
    
    email = models.EmailField(max_length=255, db_index=True)
    subscription = models.ForeignKey(HotmartSubscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    product = models.ForeignKey(HotmartProduct, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES)
    transaction_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default='BRL')
    
    raw_webhook_data = models.JSONField(help_text="Datos completos del webhook de Hotmart")
    
    processed = models.BooleanField(default=False, help_text="Si la transacción fue procesada correctamente")
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, help_text="Mensaje de error si el procesamiento falló")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} - {self.email} ({self.status})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Transacción Hotmart"
        verbose_name_plural = "Transacciones Hotmart"
        indexes = [
            models.Index(fields=['email', 'processed']),
            models.Index(fields=['event_type', 'created_at']),
        ]
