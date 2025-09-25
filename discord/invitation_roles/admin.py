from django.contrib import admin
from .models import Invite, AccessRole, BotConfiguration

@admin.register(Invite)
class InviteAdmin(admin.ModelAdmin):
    list_display = ('email', 'invite_code', 'role_id', 'status', 'created_at', 'expires_at', 'used_at', 'member_id')
    list_filter = ('status', 'created_at')
    search_fields = ('email', 'invite_code', 'member_id')
    readonly_fields = ('created_at', 'used_at')

@admin.register(AccessRole)
class AccessRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'role_id', 'is_active', 'description', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'role_id', 'description')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_active',)  # Permite activar/desactivar directamente desde la lista
    
    fieldsets = (
        ('Información del Rol', {
            'fields': ('name', 'role_id', 'description')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)  # Campo colapsable
        }),
    )


@admin.register(BotConfiguration)
class BotConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'configuration_type', 'is_active', 'description', 'updated_at')
    list_filter = ('configuration_type', 'is_active', 'created_at')
    search_fields = ('name', 'value', 'description')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_active',)
    fieldsets = (
        ('Configuración', {
            'fields': ('name', 'value', 'configuration_type', 'description')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()

# Register your models here.
