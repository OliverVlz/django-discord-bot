# 🤖 Chatbot de IA con RAG - Documentación Completa

Sistema de chatbot inteligente con **Retrieval-Augmented Generation (RAG)** integrado en Discord, especializado en odontología y la comunidad IMAX.

## 📋 Tabla de Contenidos

1. [Características Principales](#-características-principales)
2. [Sistema RAG](#-sistema-rag)
3. [Instalación y Configuración](#-instalación-y-configuración)
4. [Indexación de Datos](#-indexación-de-datos)
5. [Configuración desde Admin](#-configuración-desde-admin)
6. [Uso del Chatbot](#-uso-del-chatbot)
7. [Comandos Disponibles](#-comandos-disponibles)
8. [Gestión de Roles](#-gestión-de-roles)
9. [Troubleshooting](#-troubleshooting)

---

## 🎯 Características Principales

### ✅ **Funcionalidades Core**

- **Chat inteligente** con IA especializada en odontología
- **RAG (Retrieval-Augmented Generation)** con búsqueda vectorial
- **Base de conocimiento** indexada desde archivos de entrenamiento
- **Contexto de conversación** (memoria de mensajes anteriores)
- **Control de acceso por roles** de Discord
- **Límites de uso** (diario/mensual por rol)
- **OpenAI GPT-4o-mini** como proveedor de IA
- **Estadísticas de uso** por usuario
- **Sesiones automáticas** con expiración

### 🧠 **Sistema RAG**

- **Búsqueda vectorial** con `pgvector` y embeddings de OpenAI
- **Indexación automática** de archivos de entrenamiento
- **Contexto relevante** en cada respuesta
- **Chunks de ~500 tokens** para optimización
- **Búsqueda por similitud** usando distancia coseno

---

## 🔍 Sistema RAG

### ¿Qué es RAG?

**RAG (Retrieval-Augmented Generation)** es una técnica que combina:

1. **Retrieval**: Búsqueda de información relevante en una base de conocimiento
2. **Augmented**: Aumenta el contexto del LLM con información específica
3. **Generation**: Genera respuestas basadas en el contexto encontrado

### Cómo Funciona en Este Sistema

```
Usuario pregunta → Embedding de la pregunta → Búsqueda vectorial →
Top 5 chunks relevantes → Contexto + Prompt → LLM → Respuesta
```

### Componentes del Sistema RAG

1. **ChatbotKnowledgeChunk**: Modelo que almacena chunks vectorizados
2. **VectorService**: Servicio para crear embeddings y buscar chunks
3. **AIService**: Integra RAG en el flujo de generación
4. **index_training_data**: Comando para indexar archivos

---

## 🚀 Instalación y Configuración

### 1. Requisitos Previos

```bash
# Python 3.13+
# Django 5.2+
# PostgreSQL 16+ con extensión pgvector
# OpenAI API Key
```

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

Dependencias clave:

- `pgvector==0.3.6` - Extensión PostgreSQL para vectores
- `tiktoken>=0.9.0` - Tokenización de texto
- `aiohttp==3.12.15` - Cliente HTTP asíncrono

### 3. Configurar Base de Datos con pgvector

#### Opción A: Docker (Recomendado)

```bash
# Usar docker-compose.yml
docker-compose up -d

# O crear contenedor manualmente
docker run --name postgres-pgvector -p 5433:5432 \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=django_discord_bot \
  pgvector/pgvector:pg17
```

#### Opción B: PostgreSQL Local

```bash
# Instalar pgvector
# En PostgreSQL, ejecutar:
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4. Variables de Entorno

```env
# OpenAI (OBLIGATORIO para RAG)
OPENAI_API_KEY=sk-proj-...

# Base de datos
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DATABASE=django_discord_bot

# Discord
DISCORD_BOT_TOKEN=tu_token_aqui
```

### 5. Aplicar Migraciones

```bash
cd discord
python manage.py migrate
```

Esto creará:

- Tablas del chatbot
- Tabla `ChatbotKnowledgeChunk` con campo `embedding` vectorial
- Extensión `pgvector` en PostgreSQL

---

## 📚 Indexación de Datos

### Estructura de Archivos

Los archivos de entrenamiento deben estar en:

```
discord/chatbot_ai/ai-training/
├── Imax Launch/
│   ├── M1. Introducción.txt
│   ├── M2. Fundamentos.txt
│   └── ...
└── Imax Pro/
    ├── M1. Avanzado.txt
    └── ...
```

### Comando de Indexación

```bash
cd discord

# Ver qué se indexará (dry-run)
python manage.py index_training_data --dry-run

# Indexar todos los archivos
python manage.py index_training_data --clear
```

### Proceso de Indexación

1. **Lee archivos** `.txt` del directorio `ai-training/`
2. **Divide en chunks** de ~500 tokens con overlap de 50
3. **Crea embeddings** usando OpenAI `text-embedding-3-small`
4. **Almacena en BD** con metadatos (curso, módulo, archivo)

### Verificar Indexación

```python
from chatbot_ai.models import ChatbotKnowledgeChunk

# Contar chunks indexados
ChatbotKnowledgeChunk.objects.count()

# Ver chunks por curso
ChatbotKnowledgeChunk.objects.filter(course='imax_launch').count()
```

---

## ⚙️ Configuración desde Admin

### Acceso al Admin

```
http://127.0.0.1:8000/admin/
```

### Configuraciones del Bot

#### Configuraciones Principales:

| Nombre                    | Tipo    | Descripción                           | Ejemplo              |
| ------------------------- | ------- | ------------------------------------- | -------------------- |
| `chatbot_channel_id`      | channel | ID del canal donde funciona el bot    | `123456789012345678` |
| `default_chatbot_role_id` | general | Rol por defecto para usuarios sin rol | `987654321098765432` |
| `openai_model`            | general | Modelo de OpenAI a usar               | `gpt-4o-mini`        |

**Nota**: La API key de OpenAI se configura en `.env` como `OPENAI_API_KEY`.

### Roles del Chatbot

#### Configuración de Roles:

| Campo                  | Descripción                       | Ejemplo                    |
| ---------------------- | --------------------------------- | -------------------------- |
| `role_id`              | ID del rol de Discord             | `123456789012345678`       |
| `role_name`            | Nombre del rol                    | `VIP`, `Premium`, `Básico` |
| `daily_limit`          | Límite diario de mensajes         | `50`                       |
| `monthly_limit`        | Límite mensual de mensajes        | `1000`                     |
| `max_context_messages` | Máximo de mensajes en contexto    | `30`                       |
| `priority`             | Prioridad del rol (mayor = mejor) | `10`                       |

#### Roles Predefinidos:

- **VIP**: 50 mensajes/día, 1000/mes, contexto: 30
- **Premium**: 30 mensajes/día, 600/mes, contexto: 25
- **Básico**: 10 mensajes/día, 300/mes, contexto: 20

---

## 💬 Uso del Chatbot

### Activación del Bot

1. **Canal configurado**: El bot responde automáticamente solo en el canal configurado
2. **Permisos**: El usuario debe tener un rol configurado con acceso
3. **Mensaje fijo**: Se envía automáticamente al iniciar el bot
4. **Mensaje de bienvenida**: Se muestra en la primera interacción (se auto-elimina en 30 segundos)

### Interacción

```
Usuario: "¿Cómo hago una restauración con composite?"
Bot: "🤖 Para una restauración con composite, sigue estos pasos..."
```

### Características de la Conversación

- **Contexto**: Recuerda mensajes anteriores en la sesión
- **RAG**: Busca información relevante en la base de conocimiento
- **Especialización**: Responde sobre odontología y procedimientos
- **Seguridad**: No da diagnósticos médicos específicos
- **Tono**: Profesional pero accesible

### Flujo RAG en Cada Respuesta

1. Usuario hace pregunta
2. Sistema crea embedding de la pregunta
3. Busca 5 chunks más similares en la BD
4. Formatea contexto relevante
5. Envía contexto + pregunta al LLM
6. LLM genera respuesta basada en contexto IMAX

---

## ⚡ Comandos Disponibles

### Comandos de Usuario

| Comando     | Descripción                             | Ejemplo     |
| ----------- | --------------------------------------- | ----------- |
| `!ai_stats` | Muestra estadísticas de uso del usuario | `!ai_stats` |
| `!ai_help`  | Muestra ayuda completa del chatbot      | `!ai_help`  |
| `!ai_info`  | Muestra información básica y uso rápido | `!ai_info`  |

### Comandos de Administrador

| Comando       | Descripción                         | Permisos      |
| ------------- | ----------------------------------- | ------------- |
| `!ai_pin`     | Envía y fija mensaje de información | Administrator |
| `!ai_cleanup` | Limpia sesiones expiradas           | Administrator |
| `!ai_roles`   | Muestra roles configurados          | Administrator |

### Comandos de Django

```bash
# Indexar datos de entrenamiento
python manage.py index_training_data --clear

# Crear superusuario
python manage.py createsuperuser

# Aplicar migraciones
python manage.py migrate
```

---

## 🎭 Gestión de Roles

### Sistema de Prioridades

Los roles se evalúan por prioridad (mayor número = mayor prioridad):

```
VIP (prioridad: 10)     → Mejor acceso
Premium (prioridad: 8)  → Acceso medio
Básico (prioridad: 5)   → Acceso básico
```

### Verificación de Acceso

1. **Obtener roles del usuario** en Discord
2. **Buscar rol configurado** con mayor prioridad
3. **Verificar límites** diarios y mensuales
4. **Permitir o denegar** acceso

### Límites de Uso

- **Diario**: Se resetea cada día a medianoche
- **Mensual**: Se resetea cada mes
- **Contexto**: Máximo de mensajes recordados por sesión

### Rol por Defecto (default_chatbot_role_id)

El `default_chatbot_role_id` es el **rol de respaldo** que se asigna automáticamente a usuarios que **NO tienen ningún rol configurado**.

#### Cómo Funciona:

1. **Verificación de roles**: El bot busca si el usuario tiene algún rol configurado
2. **Si encuentra rol**: Usa los límites de ese rol específico
3. **Si NO encuentra rol**: Usa el `default_chatbot_role_id`

#### Configuraciones Recomendadas:

| Tipo de Comunidad | Configuración                                | Resultado                             |
| ----------------- | -------------------------------------------- | ------------------------------------- |
| **Abierta**       | `default_chatbot_role_id = "ID_rol_Básico"`  | Todos pueden usar con límites básicos |
| **Restringida**   | `default_chatbot_role_id = ""` (vacío)       | Solo usuarios con roles específicos   |
| **Premium**       | `default_chatbot_role_id = "ID_rol_Premium"` | Todos reciben acceso premium          |

---

## 🔧 Troubleshooting

### Problemas Comunes

#### Bot no responde

1. **Verificar canal**: ¿Está configurado `chatbot_channel_id`?
2. **Verificar permisos**: ¿El usuario tiene rol configurado?
3. **Verificar límites**: ¿Ha alcanzado límites diarios/mensuales?
4. **Verificar API**: ¿Está configurada la API key?

#### Error de RAG

1. **Verificar chunks indexados**:

   ```python
   from chatbot_ai.models import ChatbotKnowledgeChunk
   ChatbotKnowledgeChunk.objects.count()  # Debe ser > 0
   ```

2. **Re-indexar datos**:

   ```bash
   python manage.py index_training_data --clear
   ```

3. **Verificar pgvector**:
   ```sql
   SELECT * FROM pg_extension WHERE extname = 'vector';
   ```

#### Error de API

1. **Verificar API key**: ¿Es válida y tiene créditos?
2. **Verificar proveedor**: ¿Está configurado `openai_model`?
3. **Verificar internet**: ¿Hay conexión a internet?

#### Error de base de datos

1. **Verificar migraciones**: `python manage.py migrate`
2. **Verificar pgvector**: `CREATE EXTENSION IF NOT EXISTS vector;`
3. **Verificar configuración**: Variables de entorno correctas

### Logs y Debugging

```python
# Habilitar logs detallados
import logging
logging.basicConfig(level=logging.DEBUG)

# Ver chunks indexados
from chatbot_ai.models import ChatbotKnowledgeChunk
ChatbotKnowledgeChunk.objects.all()[:10]

# Ver sesiones activas
from chatbot_ai.models import ChatbotSession
ChatbotSession.objects.filter(is_active=True).count()
```

---

## 📊 Monitoreo

### Métricas Importantes

- **Chunks indexados**: Total de conocimiento en la BD
- **Consultas RAG**: Número de búsquedas vectoriales
- **Tokens consumidos**: Costo de API
- **Uso por usuario**: Mensajes diarios/mensuales

### Consultas Útiles

```python
from chatbot_ai.models import ChatbotKnowledgeChunk, ChatbotUsage

# Total de chunks
ChatbotKnowledgeChunk.objects.count()

# Chunks por curso
ChatbotKnowledgeChunk.objects.values('course').annotate(
    total=Count('id')
)

# Uso del chatbot
ChatbotUsage.objects.filter(date=timezone.now().date())
```

---

## 🚀 Mejoras Futuras

### Funcionalidades Planificadas

- 🎨 **Interfaz web** para administración
- 📊 **Dashboard** con métricas en tiempo real
- 🔄 **Fine-tuning** de embeddings
- 🎯 **Análisis de calidad** de respuestas RAG
- 📱 **Notificaciones** push para admins

### Optimizaciones

- ⚡ **Cache** de embeddings frecuentes
- 🧠 **Re-ranking** de chunks relevantes
- 📊 **A/B testing** de prompts
- 🔄 **Auto-tuning** de límites

---

**Última actualización**: Enero 2025  
**Versión**: 2.0.0  
**Compatibilidad**: Discord.py 2.6+, Django 5.2+, PostgreSQL 16+ con pgvector

