# Generated migration for chatbot_ai app

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ChatbotConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Nombre de la configuración', max_length=100, unique=True)),
                ('value', models.TextField(help_text='Valor de la configuración (JSON, texto, etc.)')),
                ('description', models.TextField(blank=True, help_text='Descripción de la configuración')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Configuración Chatbot',
                'verbose_name_plural': 'Configuraciones Chatbot',
            },
        ),
        migrations.CreateModel(
            name='ChatbotRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role_id', models.CharField(db_index=True, help_text='ID del rol de Discord', max_length=100, unique=True)),
                ('role_name', models.CharField(help_text='Nombre del rol', max_length=100)),
                ('daily_limit', models.IntegerField(default=10, help_text='Límite diario de mensajes')),
                ('monthly_limit', models.IntegerField(default=300, help_text='Límite mensual de mensajes')),
                ('max_context_messages', models.IntegerField(default=20, help_text='Máximo de mensajes en contexto')),
                ('priority', models.IntegerField(default=1, help_text='Prioridad (mayor = mejor)')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Rol Chatbot',
                'verbose_name_plural': 'Roles Chatbot',
                'ordering': ['-priority', 'role_name'],
            },
        ),
        migrations.CreateModel(
            name='ChatbotTraining',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Nombre del entrenamiento', max_length=100)),
                ('training_type', models.CharField(choices=[('system_prompt', 'Prompt del Sistema'), ('knowledge_base', 'Base de Conocimiento'), ('examples', 'Ejemplos de Conversación'), ('rules', 'Reglas Específicas')], max_length=20)),
                ('content', models.TextField(help_text='Contenido del entrenamiento')),
                ('is_active', models.BooleanField(default=True)),
                ('priority', models.IntegerField(default=1, help_text='Prioridad (mayor = mejor)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Entrenamiento Chatbot',
                'verbose_name_plural': 'Entrenamientos Chatbot',
                'ordering': ['-priority', 'name'],
            },
        ),
        migrations.CreateModel(
            name='ChatbotSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(db_index=True, help_text='ID del usuario de Discord', max_length=100)),
                ('username', models.CharField(help_text='Nombre de usuario', max_length=100)),
                ('channel_id', models.CharField(db_index=True, help_text='ID del canal donde se inició', max_length=100)),
                ('role_id', models.CharField(help_text='ID del rol del usuario', max_length=100)),
                ('is_active', models.BooleanField(default=True, help_text='Si la sesión está activa')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_activity', models.DateTimeField(auto_now=True)),
                ('expires_at', models.DateTimeField(help_text='Cuándo expira la sesión')),
            ],
            options={
                'verbose_name': 'Sesión Chatbot',
                'verbose_name_plural': 'Sesiones Chatbot',
                'ordering': ['-last_activity'],
            },
        ),
        migrations.CreateModel(
            name='ChatbotUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(db_index=True, help_text='ID del usuario', max_length=100)),
                ('role_id', models.CharField(help_text='ID del rol', max_length=100)),
                ('date', models.DateField(db_index=True, help_text='Fecha del uso')),
                ('daily_count', models.IntegerField(default=0, help_text='Contador diario')),
                ('monthly_count', models.IntegerField(default=0, help_text='Contador mensual')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Uso Chatbot',
                'verbose_name_plural': 'Usos Chatbot',
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='ChatbotMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message_id', models.CharField(db_index=True, help_text='ID del mensaje de Discord', max_length=100)),
                ('user_message', models.TextField(help_text='Mensaje del usuario')),
                ('ai_response', models.TextField(help_text='Respuesta de la IA')),
                ('tokens_used', models.IntegerField(default=0, help_text='Tokens consumidos')),
                ('processing_time', models.FloatField(default=0.0, help_text='Tiempo de procesamiento en segundos')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='chatbot_ai.chatbotsession')),
            ],
            options={
                'verbose_name': 'Mensaje Chatbot',
                'verbose_name_plural': 'Mensajes Chatbot',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='chatbotusage',
            constraint=models.UniqueConstraint(fields=('user_id', 'date'), name='unique_user_date'),
        ),
    ]



