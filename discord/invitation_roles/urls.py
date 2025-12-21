from django.urls import path
from . import views

app_name = 'invitation_roles'

urlpatterns = [
    path('generate-invite/', views.generate_invite_api, name='generate_invite_api'),
    path('hotmart/webhook/', views.hotmart_webhook, name='hotmart_webhook'),
    path('shared-invites/', views.shared_invites_api, name='shared_invites_api'),
    path('shared-invites/<uuid:link_id>/', views.shared_invite_detail_api, name='shared_invite_detail_api'),
]