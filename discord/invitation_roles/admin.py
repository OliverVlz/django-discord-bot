from django.contrib import admin
from .models import Invite, AccessRole, BotConfiguration, HotmartProduct, HotmartSubscription, HotmartTransaction, SharedInviteLink, SharedInviteRedemption

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


@admin.register(HotmartProduct)
class HotmartProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'product_id', 'discord_role_id', 'is_subscription', 'is_active', 'priority', 'updated_at')
    list_filter = ('is_subscription', 'is_active', 'priority')
    search_fields = ('product_name', 'product_id', 'discord_role_id')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_active', 'priority')
    ordering = ('-priority', 'product_name')
    
    fieldsets = (
        ('Información del Producto', {
            'fields': ('product_id', 'product_name', 'discord_role_id')
        }),
        ('Configuración', {
            'fields': ('is_subscription', 'priority', 'is_active')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(HotmartSubscription)
class HotmartSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('email', 'product', 'plan_name', 'status', 'member_id', 'next_charge_date', 'updated_at')
    list_filter = ('status', 'product', 'created_at')
    search_fields = ('email', 'subscriber_code', 'member_id', 'plan_name')
    readonly_fields = ('subscriber_code', 'created_at', 'updated_at', 'last_sync_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Información del Suscriptor', {
            'fields': ('subscriber_code', 'email', 'product', 'plan_id', 'plan_name')
        }),
        ('Estado', {
            'fields': ('status', 'next_charge_date', 'cancellation_date')
        }),
        ('Discord', {
            'fields': ('member_id', 'current_role_id')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at', 'last_sync_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


@admin.register(HotmartTransaction)
class HotmartTransactionAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'email', 'status', 'transaction_value', 'currency', 'processed', 'created_at')
    list_filter = ('event_type', 'status', 'processed', 'created_at')
    search_fields = ('email', 'transaction_id', 'hotmart_event_id')
    readonly_fields = ('transaction_id', 'hotmart_event_id', 'event_type', 'email', 'subscription', 
                      'product', 'status', 'transaction_value', 'currency', 'raw_webhook_data', 
                      'processed', 'processed_at', 'error_message', 'created_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Información del Evento', {
            'fields': ('hotmart_event_id', 'event_type', 'transaction_id', 'email')
        }),
        ('Relaciones', {
            'fields': ('subscription', 'product')
        }),
        ('Datos de la Transacción', {
            'fields': ('status', 'transaction_value', 'currency')
        }),
        ('Procesamiento', {
            'fields': ('processed', 'processed_at', 'error_message')
        }),
        ('Datos Completos del Webhook', {
            'fields': ('raw_webhook_data',),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('subscription', 'product')


@admin.register(SharedInviteLink)
class SharedInviteLinkAdmin(admin.ModelAdmin):
    list_display = ('name', 'invite_code', 'role_id', 'is_active', 'uses', 'max_uses', 'expires_at', 'last_used_at', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'invite_code', 'role_id')
    readonly_fields = ('id', 'invite_code', 'uses', 'last_used_at', 'created_at', 'updated_at')
    list_editable = ('is_active',)


@admin.register(SharedInviteRedemption)
class SharedInviteRedemptionAdmin(admin.ModelAdmin):
    list_display = ('member_id', 'link', 'status', 'created_at', 'used_at')
    list_filter = ('status', 'created_at')
    search_fields = ('member_id', 'link__invite_code', 'link__name')
    readonly_fields = ('id', 'created_at', 'used_at')
