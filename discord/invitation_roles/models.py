from django.db import models
from uuid import uuid4

# Create your models here.

class Invite(models.Model):
    INVITE_STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('USED', 'Usado'),
        ('EXPIRED', 'Expirado'),
    ]

    invite_code = models.CharField(max_length=20, unique=True, db_index=True)
    role_id = models.CharField(max_length=100) # ID del rol de Discord
    email = models.EmailField(max_length=255)
    status = models.CharField(max_length=10, choices=INVITE_STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    member_id = models.CharField(max_length=100, null=True, blank=True) # ID del miembro de Discord

    def __str__(self):
        return f"{self.email} - {self.invite_code} ({self.status})"

    class Meta:
        ordering = ['created_at']
