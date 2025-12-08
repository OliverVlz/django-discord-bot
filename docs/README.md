# 🤖 Bot de Discord para IMAX - Documentación Completa

Sistema completo de gestión de comunidad Discord con integración Hotmart, chatbot de IA con RAG, y administración automatizada de roles.

## 📋 Tabla de Contenidos

1. [Características Principales](#-características-principales)
2. [Instalación Rápida](#-instalación-rápida)
3. [Documentación por Módulo](#-documentación-por-módulo)
4. [Arquitectura del Sistema](#-arquitectura-del-sistema)
5. [Requisitos](#-requisitos)

---

## 🎯 Características Principales

### ✅ **Módulos del Sistema**

- **🤖 Chatbot de IA con RAG**: Asistente inteligente especializado en odontología con búsqueda vectorial
- **🛒 Integración Hotmart**: Gestión automática de suscripciones y roles de Discord
- **🎭 Sistema de Roles**: Control de acceso granular con límites personalizables
- **📧 Invitaciones Automáticas**: Generación y envío de invites únicos por email
- **📊 Panel de Administración**: Django Admin completo para gestión

### 🧠 **Chatbot con RAG (Retrieval-Augmented Generation)**

- Búsqueda vectorial con **pgvector** y **OpenAI embeddings**
- Base de conocimiento indexada desde archivos de entrenamiento
- Contexto relevante automático en cada respuesta
- Límites de uso por rol (diario/mensual)
- Sesiones persistentes con memoria contextual

### 🛒 **Integración Hotmart**

- Webhooks automáticos para eventos de compra
- Gestión de suscripciones recurrentes
- Asignación automática de roles según producto
- Soporte para upgrades/downgrades
- Revocación automática al cancelar

---

## 🚀 Instalación Rápida

### 1. Clonar y Configurar

```bash
git clone <tu-repositorio>
cd django-discord-bot

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate      # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# Discord
DISCORD_BOT_TOKEN=tu_token_aqui
CLIENT_ID=tu_client_id

# OpenAI (para chatbot y RAG)
OPENAI_API_KEY=sk-proj-...

# Base de Datos PostgreSQL con pgvector
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DATABASE=django_discord_bot

# Django
DJANGO_SECRET_KEY=tu_secret_key_aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 3. Configurar Base de Datos

```bash
cd discord
python manage.py migrate
python manage.py createsuperuser
```

### 4. Indexar Datos de Entrenamiento (RAG)

```bash
python manage.py index_training_data --clear
```

### 5. Iniciar el Sistema

```bash
# Opción A: Desarrollo local
python bot.py

# Opción B: Con Docker
docker-compose up --build
```

---

## 📚 Documentación por Módulo

### 🤖 [Chatbot de IA con RAG](./CHATBOT_IA.md)

Documentación completa del sistema de chatbot:

- Configuración de RAG con pgvector
- Indexación de datos de entrenamiento
- Comandos disponibles
- Gestión de roles y límites
- Troubleshooting

### 🛒 [Integración Hotmart](./HOTMART.md)

Guía de integración con Hotmart:

- Configuración de webhooks
- Eventos soportados
- Gestión de suscripciones
- Asignación automática de roles
- Casos de uso y ejemplos

### 🚀 [Despliegue en Producción](./DEPLOYMENT.md)

Guía de despliegue:

- Docker y Docker Compose
- Configuración de Nginx
- Despliegue en Dokploy
- Variables de entorno
- Troubleshooting

### ⚙️ [Configuración Inicial](./SETUP.md)

Guía paso a paso de configuración:

- Instalación de dependencias
- Configuración de base de datos
- Configuración del bot
- Primeros pasos

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────┐
│                    Discord Server                        │
└───────────────┬─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────┐
│              Discord Bot (bot.py)                       │
│  • Gestión de roles                                      │
│  • Comandos de usuario                                   │
│  • Chatbot de IA                                         │
└───────────────┬─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────┐
│            Django Application                            │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │ invitation_roles│  │  chatbot_ai      │            │
│  │ • Hotmart        │  │  • RAG           │            │
│  │ • Invites        │  │  • AI Service    │            │
│  │ • Roles          │  │  • Vector Search │            │
│  └──────────────────┘  └──────────────────┘            │
└───────────────┬─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────┐
│         PostgreSQL + pgvector                            │
│  • Modelos Django                                        │
│  • Embeddings vectoriales                               │
│  • Búsqueda por similitud                               │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 Requisitos

### Software

- **Python**: 3.13+
- **PostgreSQL**: 16+ con extensión `pgvector`
- **Docker**: Opcional, para desarrollo local
- **Git**: Para clonar el repositorio

### Servicios Externos

- **Discord**: Bot token y permisos del servidor
- **OpenAI**: API key para embeddings y chat
- **Hotmart**: Webhook configurado (opcional)
- **Gmail**: Email y app password para envío de correos (opcional)

### Dependencias Principales

- `Django==5.2.6`
- `discord.py==2.6.3`
- `pgvector==0.3.6`
- `tiktoken>=0.9.0`
- `aiohttp==3.12.15`

Ver `requirements.txt` para lista completa.

---

## 🆘 Soporte

### Recursos

- **Documentación**: Esta carpeta `docs/`
- **Issues**: Reportar problemas en el repositorio
- **Logs**: Revisar logs del bot y Django para debugging

### Comandos Útiles

```bash
# Ver logs del bot
python bot.py

# Verificar estado de la base de datos
cd discord
python manage.py shell
>>> from chatbot_ai.models import ChatbotKnowledgeChunk
>>> ChatbotKnowledgeChunk.objects.count()

# Re-indexar datos de entrenamiento
python manage.py index_training_data --clear
```

---

## 📝 Licencia

[Especificar licencia si aplica]

---

**Última actualización**: Enero 2025  
**Versión**: 2.0.0
