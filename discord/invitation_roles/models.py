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
    value = models.CharField(max_length=200, help_text="Valor de la configuración (ID de Discord, número, etc.)")
    configuration_type = models.CharField(max_length=20, choices=CONFIGURATION_TYPES, help_text="Tipo de configuración")
    description = models.TextField(blank=True, help_text="Descripción de para qué se usa esta configuración")
    is_active = models.BooleanField(default=True, help_text="Si está activa, el bot la usará")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Validar que solo haya una configuración activa por nombre
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
