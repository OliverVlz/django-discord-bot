from django.urls import path
from . import views

app_name = 'invitation_roles'

urlpatterns = [
    path('generate-invite/', views.generate_invite_api, name='generate_invite_api'),
]