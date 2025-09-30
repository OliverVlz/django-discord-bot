from django.core.management.base import BaseCommand
from invitation_roles.models import BotConfiguration
import os


class Command(BaseCommand):
    help = 'Puebla las configuraciones iniciales del bot desde variables de entorno'

    def handle(self, *args, **options):
        # Configuraciones a migrar desde .env a BD
        configurations = [
            {
                'name': 'guild_id',
                'value': os.environ.get('GUILD_ID', ''),
                'configuration_type': 'guild',
                'description': 'ID del servidor de Discord donde opera el bot'
            },
            {
                'name': 'welcome_channel_id',
                'value': os.environ.get('DEFAULT_CHANNEL_ID', ''),
                'configuration_type': 'channel',
                'description': 'Canal de bienvenida donde se muestran mensajes de orientación'
            },
            {
                'name': 'rules_channel_id',
                'value': os.environ.get('RULES_CHANNEL_ID', ''),
                'configuration_type': 'channel',
                'description': 'Canal donde se muestran las reglas del servidor'
            },
            {
                'name': 'rules_message_id',
                'value': os.environ.get('RULES_MESSAGE_ID', ''),
                'configuration_type': 'message',
                'description': 'ID del mensaje de reglas con el botón de aceptación'
            },
            {
                'name': 'presentation_channel_id',
                'value': os.environ.get('PRESENTATION_CHANNEL_ID', ''),
                'configuration_type': 'channel',
                'description': 'Canal donde los usuarios se presentan'
            },
            {
                'name': 'presentation_message_id',
                'value': os.environ.get('PRESENTATION_MESSAGE_ID', ''),
                'configuration_type': 'message',
                'description': 'ID del mensaje fijado en el canal de presentaciones'
            },
            {
                'name': 'invite_ttl_seconds',
                'value': os.environ.get('INVITE_TTL_SECONDS', '86400'),
                'configuration_type': 'general',
                'description': 'Tiempo de vida de las invitaciones en segundos (por defecto 24 horas)'
            },
            {
                'name': 'welcome_message_id',
                'value': '',  # Se creará automáticamente cuando el bot envíe el mensaje
                'configuration_type': 'message',
                'description': 'ID del mensaje fijado en el canal de bienvenida (default channel)'
            },
        ]

        for config_data in configurations:
            # Crear configuraciones con valor o si son de tipo 'message' (se llenarán automáticamente)
            if config_data['value'] or config_data['configuration_type'] == 'message':
                config, created = BotConfiguration.objects.get_or_create(
                    name=config_data['name'],
                    defaults={
                        'value': config_data['value'],
                        'configuration_type': config_data['configuration_type'],
                        'description': config_data['description'],
                        'is_active': True
                    }
                )
                
                if created:
                    if config_data['value']:
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ Configuración creada: {config_data["name"]} = {config_data["value"]}')
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ Configuración creada (se llenará automáticamente): {config_data["name"]}')
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Configuración ya existe: {config_data["name"]}')
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Configuración {config_data["name"]} no tiene valor en .env, omitiendo')
                )

        self.stdout.write(
            self.style.SUCCESS('\n🎉 Proceso completado. Revisa las configuraciones en Django Admin.')
        )
        self.stdout.write(
            self.style.WARNING('\n📝 IMPORTANTE: Después de verificar que todo funciona correctamente,')
        )
        self.stdout.write(
            self.style.WARNING('   puedes remover estas variables del .env:')
        )
        self.stdout.write(
            self.style.WARNING('   - GUILD_ID, DEFAULT_CHANNEL_ID (ahora welcome_channel_id), RULES_CHANNEL_ID, etc.')
        )
        self.stdout.write(
            self.style.WARNING('   Mantén solo las variables sensibles como DISCORD_BOT_TOKEN.')
        )
