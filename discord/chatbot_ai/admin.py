from django.contrib import admin
from .models import (
    ChatbotConfiguration, ChatbotRole, ChatbotSession, 
    ChatbotMessage, ChatbotUsage, ChatbotTraining
)

@admin.register(ChatbotConfiguration)
class ChatbotConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ChatbotRole)
class ChatbotRoleAdmin(admin.ModelAdmin):
    list_display = ['role_name', 'role_id', 'daily_limit', 'monthly_limit', 'priority', 'is_active']
    list_filter = ['is_active', 'priority']
    search_fields = ['role_name', 'role_id']
    ordering = ['-priority', 'role_name']

@admin.register(ChatbotSession)
class ChatbotSessionAdmin(admin.ModelAdmin):
    list_display = ['username', 'user_id', 'channel_id', 'is_active', 'created_at', 'expires_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['username', 'user_id', 'channel_id']
    readonly_fields = ['created_at', 'last_activity']

@admin.register(ChatbotMessage)
class ChatbotMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'tokens_used', 'processing_time', 'created_at']
    list_filter = ['created_at', 'tokens_used']
    search_fields = ['user_message', 'ai_response']
    readonly_fields = ['created_at']

@admin.register(ChatbotUsage)
class ChatbotUsageAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'date', 'daily_count', 'monthly_count']
    list_filter = ['date']
    search_fields = ['user_id']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ChatbotTraining)
class ChatbotTrainingAdmin(admin.ModelAdmin):
    list_display = ['name', 'training_type', 'priority', 'is_active', 'created_at']
    list_filter = ['training_type', 'is_active', 'priority']
    search_fields = ['name', 'content']
    ordering = ['-priority', 'name']