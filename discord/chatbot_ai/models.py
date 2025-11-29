from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
import json
from pgvector.django import VectorField

class ChatbotConfiguration(models.Model):
    """Configuración del chatbot de IA"""
    
    name = models.CharField(max_length=100, unique=True, help_text="Nombre de la configuración")
    value = models.TextField(help_text="Valor de la configuración (JSON, texto, etc.)")
    description = models.TextField(blank=True, help_text="Descripción de la configuración")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name}: {self.value[:50]}..."
    
    class Meta:
        verbose_name = "Configuración Chatbot"
        verbose_name_plural = "Configuraciones Chatbot"


class ChatbotRole(models.Model):
    """Roles que pueden usar el chatbot con sus límites"""
    
    role_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="ID del rol de Discord")
    role_name = models.CharField(max_length=100, help_text="Nombre del rol")
    daily_limit = models.IntegerField(default=10, help_text="Límite diario de mensajes")
    monthly_limit = models.IntegerField(default=300, help_text="Límite mensual de mensajes")
    max_context_messages = models.IntegerField(default=20, help_text="Máximo de mensajes en contexto")
    priority = models.IntegerField(default=1, help_text="Prioridad (mayor = mejor)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.role_name} (Límite: {self.daily_limit}/día)"
    
    class Meta:
        ordering = ['-priority', 'role_name']
        verbose_name = "Rol Chatbot"
        verbose_name_plural = "Roles Chatbot"


class ChatbotSession(models.Model):
    """Sesión de conversación con el chatbot"""
    
    user_id = models.CharField(max_length=100, db_index=True, help_text="ID del usuario de Discord")
    username = models.CharField(max_length=100, help_text="Nombre de usuario")
    channel_id = models.CharField(max_length=100, db_index=True, help_text="ID del canal donde se inició")
    role_id = models.CharField(max_length=100, help_text="ID del rol del usuario")
    is_active = models.BooleanField(default=True, help_text="Si la sesión está activa")
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(help_text="Cuándo expira la sesión")
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Sesión expira en 24 horas por defecto
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def __str__(self):
        status = "🟢" if self.is_active and not self.is_expired() else "🔴"
        return f"{status} {self.username} ({self.channel_id})"
    
    class Meta:
        ordering = ['-last_activity']
        verbose_name = "Sesión Chatbot"
        verbose_name_plural = "Sesiones Chatbot"


class ChatbotMessage(models.Model):
    """Mensajes de conversación con el chatbot"""
    
    session = models.ForeignKey(ChatbotSession, on_delete=models.CASCADE, related_name='messages')
    message_id = models.CharField(max_length=100, db_index=True, help_text="ID del mensaje de Discord")
    user_message = models.TextField(help_text="Mensaje del usuario")
    ai_response = models.TextField(help_text="Respuesta de la IA")
    tokens_used = models.IntegerField(default=0, help_text="Tokens consumidos")
    processing_time = models.FloatField(default=0.0, help_text="Tiempo de procesamiento en segundos")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.session.username}: {self.user_message[:50]}..."
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Mensaje Chatbot"
        verbose_name_plural = "Mensajes Chatbot"


class ChatbotUsage(models.Model):
    """Registro de uso del chatbot por usuario y período"""
    
    user_id = models.CharField(max_length=100, db_index=True, help_text="ID del usuario")
    role_id = models.CharField(max_length=100, help_text="ID del rol")
    date = models.DateField(db_index=True, help_text="Fecha del uso")
    daily_count = models.IntegerField(default=0, help_text="Contador diario")
    monthly_count = models.IntegerField(default=0, help_text="Contador mensual")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user_id} - {self.date}: {self.daily_count}"
    
    class Meta:
        unique_together = ['user_id', 'date']
        ordering = ['-date']
        verbose_name = "Uso Chatbot"
        verbose_name_plural = "Usos Chatbot"


class ChatbotTraining(models.Model):
    """Entrenamiento personalizado del chatbot"""
    
    TRAINING_TYPES = [
        ('system_prompt', 'Prompt del Sistema'),
        ('knowledge_base', 'Base de Conocimiento'),
        ('examples', 'Ejemplos de Conversación'),
        ('rules', 'Reglas Específicas'),
    ]
    
    name = models.CharField(max_length=100, help_text="Nombre del entrenamiento")
    training_type = models.CharField(max_length=20, choices=TRAINING_TYPES)
    content = models.TextField(help_text="Contenido del entrenamiento")
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=1, help_text="Prioridad (mayor = mejor)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.training_type})"
    
    class Meta:
        ordering = ['-priority', 'name']
        verbose_name = "Entrenamiento Chatbot"
        verbose_name_plural = "Entrenamientos Chatbot"


class ChatbotKnowledgeChunk(models.Model):
    """Chunks de conocimiento vectorizados para RAG"""
    
    COURSE_CHOICES = [
        ('imax_launch', 'IMAX Launch'),
        ('imax_pro', 'IMAX Pro'),
    ]
    
    content = models.TextField(help_text="Contenido del chunk (~500 tokens)")
    embedding = VectorField(dimensions=1536, help_text="Vector embedding de OpenAI")
    source_file = models.CharField(max_length=255, help_text="Archivo de origen")
    course = models.CharField(max_length=20, choices=COURSE_CHOICES, db_index=True)
    module = models.CharField(max_length=100, blank=True, help_text="Módulo extraído del nombre")
    chunk_index = models.IntegerField(default=0, help_text="Índice del chunk en el archivo")
    token_count = models.IntegerField(default=0, help_text="Número de tokens en el chunk")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.course} - {self.source_file[:30]}... (chunk {self.chunk_index})"
    
    class Meta:
        ordering = ['course', 'source_file', 'chunk_index']
        verbose_name = "Chunk de Conocimiento"
        verbose_name_plural = "Chunks de Conocimiento"
        indexes = [
            models.Index(fields=['course', 'source_file']),
        ]