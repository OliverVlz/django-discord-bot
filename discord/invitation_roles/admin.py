from django.contrib import admin
from .models import Invite

@admin.register(Invite)
class InviteAdmin(admin.ModelAdmin):
    list_display = ('email', 'invite_code', 'role_id', 'status', 'created_at', 'expires_at', 'used_at', 'member_id')
    list_filter = ('status', 'created_at')
    search_fields = ('email', 'invite_code', 'member_id')
    readonly_fields = ('created_at', 'used_at')

# Register your models here.
