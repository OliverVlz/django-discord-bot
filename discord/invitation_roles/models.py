from django.db import models
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
