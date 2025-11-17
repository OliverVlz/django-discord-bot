from django.core.management.base import BaseCommand
from django.db import transaction
from invitation_roles.models import BotConfiguration
from chatbot_ai.models import (
    ChatbotRole, ChatbotConfiguration, ChatbotTraining
)

class Command(BaseCommand):
    help = 'Configura el chatbot de IA con configuraciones básicas'

    def handle(self, *args, **options):
        self.stdout.write("🚀 Configurando Chatbot de IA para Discord...")
        self.stdout.write("=" * 50)
        
        try:
            self.setup_bot_configurations()
            self.setup_chatbot_roles()
            self.setup_system_prompt()
            self.setup_training_examples()
            
            self.stdout.write("=" * 50)
            self.stdout.write(
                self.style.SUCCESS("✅ Configuración completada!")
            )
            self.stdout.write("")
            self.stdout.write("📋 Próximos pasos:")
            self.stdout.write("1. Configurar variables de entorno:")
            self.stdout.write("   - OPENAI_API_KEY o GEMINI_API_KEY")
            self.stdout.write("   - AI_PROVIDER (openai o gemini)")
            self.stdout.write("")
            self.stdout.write("2. Actualizar configuraciones en el admin de Django:")
            self.stdout.write("   - chatbot_channel_id: ID del canal donde funcionará el bot")
            self.stdout.write("   - default_chatbot_role_id: Rol por defecto")
            self.stdout.write("")
            self.stdout.write("3. Configurar roles en el admin:")
            self.stdout.write("   - Editar IDs de roles reales de tu servidor")
            self.stdout.write("   - Ajustar límites según necesidades")
            self.stdout.write("")
            self.stdout.write("4. Reiniciar el bot de Discord")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error durante la configuración: {e}")
            )

    def setup_bot_configurations(self):
        """Configura las configuraciones básicas del bot"""
        self.stdout.write("🔧 Configurando configuraciones del bot...")
        
        configs = [
            {
                'name': 'chatbot_channel_id',
                'value': '',  # Se debe configurar manualmente
                'configuration_type': 'channel',
                'description': 'ID del canal donde funciona el chatbot de IA'
            },
            {
                'name': 'default_chatbot_role_id',
                'value': '',  # Se debe configurar manualmente
                'configuration_type': 'general',
                'description': 'ID del rol por defecto para usuarios sin rol específico'
            },
            {
                'name': 'ai_provider',
                'value': 'openai',
                'configuration_type': 'general',
                'description': 'Proveedor de IA (openai, gemini)'
            },
            {
                'name': 'openai_api_key',
                'value': '',  # Se debe configurar manualmente
                'configuration_type': 'api_key',
                'description': 'API Key de OpenAI (sk-...)'
            },
            {
                'name': 'gemini_api_key',
                'value': '',  # Se debe configurar manualmente
                'configuration_type': 'api_key',
                'description': 'API Key de Google Gemini (AI...)'
            }
        ]
        
        for config_data in configs:
            config, created = BotConfiguration.objects.get_or_create(
                name=config_data['name'],
                defaults=config_data
            )
            if created:
                self.stdout.write(f"✅ Configuración creada: {config_data['name']}")
            else:
                self.stdout.write(f"ℹ️ Configuración ya existe: {config_data['name']}")

    def setup_chatbot_roles(self):
        """Configura roles básicos para el chatbot"""
        self.stdout.write("🎭 Configurando roles del chatbot...")
        
        # Ejemplo de roles - ajustar según tu servidor
        roles = [
            {
                'role_id': '123456789012345678',  # Cambiar por ID real
                'role_name': 'VIP',
                'daily_limit': 50,
                'monthly_limit': 1000,
                'max_context_messages': 30,
                'priority': 10
            },
            {
                'role_id': '123456789012345679',  # Cambiar por ID real
                'role_name': 'Premium',
                'daily_limit': 30,
                'monthly_limit': 600,
                'max_context_messages': 25,
                'priority': 8
            },
            {
                'role_id': '123456789012345680',  # Cambiar por ID real
                'role_name': 'Básico',
                'daily_limit': 10,
                'monthly_limit': 300,
                'max_context_messages': 20,
                'priority': 5
            }
        ]
        
        for role_data in roles:
            role, created = ChatbotRole.objects.get_or_create(
                role_id=role_data['role_id'],
                defaults=role_data
            )
            if created:
                self.stdout.write(f"✅ Rol creado: {role_data['role_name']}")
            else:
                self.stdout.write(f"ℹ️ Rol ya existe: {role_data['role_name']}")

    def setup_system_prompt(self):
        """Configura el prompt del sistema"""
        self.stdout.write("🤖 Configurando prompt del sistema...")
        
        system_prompt = """Eres un asistente de IA especializado en odontología y la comunidad IMAX. 

CARACTERÍSTICAS:
- Eres experto en odontología, tratamientos, procedimientos y mejores prácticas
- Respondes de manera profesional pero amigable
- Mantienes un tono educativo y constructivo
- Siempre recomiendas consultar con profesionales cuando sea necesario
- Respetas las reglas de la comunidad IMAX

REGLAS IMPORTANTES:
1. NUNCA proporciones diagnósticos médicos específicos
2. Siempre recomienda consultar con un dentista profesional para casos específicos
3. Mantén las conversaciones educativas y constructivas
4. Respeta los diferentes niveles de conocimiento de los usuarios
5. Si no estás seguro de algo, dilo claramente

RESPUESTAS:
- Sé conciso pero completo
- Usa emojis moderadamente
- Incluye referencias cuando sea apropiado
- Mantén un tono profesional pero accesible

ESPECIALIDADES:
- Odontología general y especializada
- Procedimientos clínicos
- Materiales dentales
- Técnicas de tratamiento
- Prevención y cuidado oral
- Tecnología dental moderna"""
        
        # Usar ChatbotConfiguration en lugar de BotConfiguration para texto largo
        config, created = ChatbotConfiguration.objects.get_or_create(
            name='system_prompt',
            defaults={
                'value': system_prompt,
                'description': 'Prompt del sistema para el chatbot de IA'
            }
        )
        
        if created:
            self.stdout.write("✅ Prompt del sistema configurado")
        else:
            self.stdout.write("ℹ️ Prompt del sistema ya existe")

    def setup_training_examples(self):
        """Configura ejemplos de entrenamiento"""
        self.stdout.write("📚 Configurando ejemplos de entrenamiento...")
        
        examples = [
            {
                'name': 'Ejemplos de Procedimientos',
                'training_type': 'examples',
                'content': """Ejemplos de conversaciones sobre procedimientos:

Usuario: "¿Cómo hago una restauración con composite?"
Asistente: "Para una restauración con composite, sigue estos pasos principales:

1. **Preparación**: Aislamiento absoluto del campo operatorio
2. **Acondicionamiento**: Grabado ácido del esmalte y dentina
3. **Aplicación del adhesivo**: Siguiendo las instrucciones del fabricante
4. **Colocación del composite**: En incrementos de 2mm máximo
5. **Polimerización**: 20 segundos por incremento
6. **Acabado y pulido**: Para lograr la anatomía y brillo adecuados

⚠️ Recuerda que cada caso es único y siempre consulta las indicaciones específicas del material que uses.""",
                'priority': 10
            },
            {
                'name': 'Base de Conocimiento IMAX',
                'training_type': 'knowledge_base',
                'content': """Información sobre la comunidad IMAX:

IMAX es una comunidad de profesionales de la odontología que se enfoca en:
- Educación continua en odontología
- Intercambio de experiencias clínicas
- Mejores prácticas en tratamientos
- Tecnología dental moderna
- Networking profesional

La comunidad tiene diferentes niveles:
- Básico: Fundamentos y conceptos generales
- Premium: Técnicas avanzadas y casos complejos
- VIP: Acceso completo y mentorías personalizadas

Reglas de la comunidad:
1. Respeto mutuo entre miembros
2. Compartir conocimientos de manera constructiva
3. Mantener discusiones profesionales
4. No hacer spam ni autopromoción
5. Usar los canales apropiados para cada tema""",
                'priority': 9
            }
        ]
        
        for example in examples:
            training, created = ChatbotTraining.objects.get_or_create(
                name=example['name'],
                defaults=example
            )
            if created:
                self.stdout.write(f"✅ Entrenamiento creado: {example['name']}")
            else:
                self.stdout.write(f"ℹ️ Entrenamiento ya existe: {example['name']}")
