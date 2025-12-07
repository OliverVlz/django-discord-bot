import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'discord'))
from dotenv import load_dotenv

load_dotenv()

print("=" * 50)
print("🔍 Verificación de Base de Datos")
print("=" * 50)
print()
print("Variables de entorno (.env):")
print(f"  POSTGRES_HOST: {os.environ.get('POSTGRES_HOST', 'NO CONFIGURADO')}")
print(f"  POSTGRES_PORT: {os.environ.get('POSTGRES_PORT', 'NO CONFIGURADO')}")
print(f"  POSTGRES_DATABASE: {os.environ.get('POSTGRES_DATABASE', 'NO CONFIGURADO')}")
print(f"  POSTGRES_USER: {os.environ.get('POSTGRES_USER', 'NO CONFIGURADO')}")
print()

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'discord.discord.settings')
django.setup()

from django.conf import settings
from invitation_roles.models import BotConfiguration

print("Configuración Django (settings.py):")
print(f"  HOST: {settings.DATABASES['default']['HOST']}")
print(f"  PORT: {settings.DATABASES['default']['PORT']}")
print(f"  DATABASE: {settings.DATABASES['default']['NAME']}")
print(f"  USER: {settings.DATABASES['default']['USER']}")
print()

print("Configuraciones en BD:")
configs = BotConfiguration.objects.all()
print(f"  Total: {configs.count()}")
for config in configs[:5]:
    print(f"    - {config.name}: {config.value} (active: {config.is_active})")

