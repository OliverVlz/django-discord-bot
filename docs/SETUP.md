# ⚙️ Guía de Configuración Inicial

Guía paso a paso para configurar el bot de Discord desde cero.

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#-requisitos-previos)
2. [Instalación de Dependencias](#-instalación-de-dependencias)
3. [Configuración de Base de Datos](#-configuración-de-base-de-datos)
4. [Configuración del Bot](#-configuración-del-bot)
5. [Configuración del Chatbot](#-configuración-del-chatbot)
6. [Primera Ejecución](#-primera-ejecución)
7. [Verificación](#-verificación)

---

## 📦 Requisitos Previos

### Software Necesario

- **Python**: 3.13 o superior
- **PostgreSQL**: 16+ con extensión `pgvector`
- **Git**: Para clonar el repositorio
- **Docker**: Opcional, para desarrollo local

### Cuentas y Tokens

- **Discord**: Bot token y permisos del servidor
- **OpenAI**: API key para embeddings y chat
- **Hotmart**: Webhook configurado (opcional)
- **Gmail**: App password para envío de emails (opcional)

---

## 🔧 Instalación de Dependencias

### 1. Clonar Repositorio

```bash
git clone <tu-repositorio>
cd django-discord-bot
```

### 2. Crear Entorno Virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Verificar Instalación

```bash
python --version  # Debe ser 3.13+
pip list | grep Django  # Debe mostrar Django 5.2.6
pip list | grep discord  # Debe mostrar discord.py 2.6.3
```

---

## 🗄️ Configuración de Base de Datos

### Opción A: Docker (Recomendado para Desarrollo)

```bash
# Iniciar PostgreSQL con pgvector
docker run --name postgres-pgvector -p 5433:5432 \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=django_discord_bot \
  -d pgvector/pgvector:pg17

# Verificar que está corriendo
docker ps | grep postgres-pgvector
```

### Opción B: PostgreSQL Local

1. Instalar PostgreSQL 16+
2. Instalar extensión pgvector:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

### Configurar Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# Base de Datos
POSTGRES_HOST=localhost
POSTGRES_PORT=5433  # 5432 si es PostgreSQL local
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DATABASE=django_discord_bot

# Discord
DISCORD_BOT_TOKEN=tu_token_aqui
CLIENT_ID=tu_client_id

# OpenAI (OBLIGATORIO para chatbot y RAG)
OPENAI_API_KEY=sk-proj-...

# Django
DJANGO_SECRET_KEY=tu_secret_key_aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# Email (Gmail - opcional)
GMAIL_ADDRESS=tu-email@gmail.com
GMAIL_APP_PASSWORD=tu-app-password
```

**Configurar Gmail App Password:**

1. Ve a [myaccount.google.com](https://myaccount.google.com)
2. Activa la **verificación en dos pasos** (requerida)
3. Ve a **Seguridad** → **Contraseñas de aplicaciones**
4. Selecciona **Correo** y **Otro (personalizado)** → Escribe "Discord Bot"
5. Copia la contraseña de 16 caracteres generada
6. Úsala como `GMAIL_APP_PASSWORD` en `.env`

### Aplicar Migraciones

```bash
cd discord
python manage.py migrate
```

Esto creará todas las tablas necesarias:

- Modelos de `invitation_roles`
- Modelos de `chatbot_ai`
- Extensión `pgvector` en PostgreSQL

### Habilitar pgvector (si no se hizo automáticamente)

```bash
# Conectarse a PostgreSQL
psql -h localhost -p 5433 -U postgres -d django_discord_bot

# Ejecutar
CREATE EXTENSION IF NOT EXISTS vector;

# Verificar
\dx vector
```

---

## 🤖 Configuración del Bot

### 1. Crear Bot en Discord

1. Ve a [Discord Developer Portal](https://discord.com/developers/applications)
2. Crea una nueva aplicación
3. Ve a "Bot" → "Add Bot"
4. Copia el **Bot Token**
5. Habilita estos permisos:
   - ✅ Manage Roles
   - ✅ Send Messages
   - ✅ Read Message History
   - ✅ Use External Emojis
   - ✅ Manage Messages

### 2. Invitar Bot al Servidor

1. Ve a "OAuth2" → "URL Generator"
2. Selecciona scopes: `bot`, `applications.commands`
3. Selecciona permisos necesarios
4. Copia la URL y ábrela en el navegador
5. Selecciona tu servidor y autoriza

### 3. Configurar Variables de Entorno

Agregar a `.env`:

```env
DISCORD_BOT_TOKEN=tu_token_copiado
CLIENT_ID=tu_client_id
```

### 4. Obtener IDs de Discord

Para configurar el bot necesitarás estos IDs:

- **Guild ID**: ID del servidor
- **Channel IDs**: IDs de canales (bienvenida, reglas, chatbot)
- **Role IDs**: IDs de roles a asignar

**Cómo obtener IDs:**

1. Activa "Modo Desarrollador" en Discord (Configuración → Avanzado)
2. Click derecho en servidor/canal/rol → "Copiar ID"

---

## 🧠 Configuración del Chatbot

### 1. Crear Superusuario

```bash
cd discord
python manage.py createsuperuser
```

Sigue las instrucciones para crear un usuario admin.

### 2. Acceder al Admin

```bash
# Iniciar servidor Django
python manage.py runserver
```

Abre en el navegador: `http://127.0.0.1:8000/admin/`

### 3. Configurar Bot Configurations

Ir a: **Invitation Roles → Bot Configurations**

Crear estas configuraciones:

| Name                      | Value        | Type    | Description                 |
| ------------------------- | ------------ | ------- | --------------------------- |
| `guild_id`                | `1234567890` | guild   | ID del servidor Discord     |
| `chatbot_channel_id`      | `1234567890` | channel | Canal del chatbot           |
| `welcome_channel_id`      | `1234567890` | channel | Canal de bienvenida         |
| `rules_channel_id`        | `1234567890` | channel | Canal de reglas             |
| `default_chatbot_role_id` | `1234567890` | general | Rol por defecto del chatbot |

### 3.1 API de invitaciones (opcional)

Estos endpoints viven bajo el prefijo `/invitation_roles/`.

#### A) Crear invitación compartida por rol

**POST** `/invitation_roles/shared-invites/`

**Headers:**

- `Content-Type: application/json`
- `X-API-Key: <api_key>` (solo si configuraste `invitation_roles_api_key` en **Invitation Roles → Bot Configurations**)

**Body (JSON):**

- `roleId` (requerido): ID del rol de Discord.
- `maxUses` (requerido, entero): cantidad máxima de usos.
  - `0` = sin límite de usos (ilimitado).
  - `1` a `100` = límite de usos.
  - Valores mayores a `100` suelen ser rechazados por la API de Discord.
- `ttlSeconds` (opcional, entero): tiempo de vida en segundos.
  - 1 día: `86400`
  - 7 días (máximo en Discord): `604800`
  - `0` = sin expiración (Discord lo maneja como `max_age = 0`).
- `name` (opcional): nombre descriptivo.

Ejemplo (7 días):

```json
{
  "roleId": "123456789012345678",
  "maxUses": 25,
  "ttlSeconds": 604800,
  "name": "Invitación 7 días"
}
```

Ejemplo (sin expiración y sin límite de usos):

```json
{
  "roleId": "123456789012345678",
  "maxUses": 0,
  "ttlSeconds": 0,
  "name": "Invitación sin expiración"
}
```

Respuesta: `201` con un objeto `item` que incluye `inviteUrl`, `inviteCode`, `remainingUses`, `expiresAt`, etc.

#### B) Crear invitación de 1 uso para un email (envía correo)

**POST** `/invitation_roles/generate-invite/`

**Body (JSON):**

```json
{
  "email": "persona@ejemplo.com",
  "roleId": "123456789012345678"
}
```

Respuesta: `200` con `inviteUrl` (y envía el correo si Gmail está configurado).

### 4. Configurar Roles del Chatbot

Ir a: **Chatbot AI → Chatbot Roles → Add**

Crear roles con límites:

**Ejemplo - Rol VIP:**

- Role ID: `123456789012345678`
- Role Name: `VIP`
- Daily Limit: `50`
- Monthly Limit: `1000`
- Max Context Messages: `30`
- Priority: `10`
- Is Active: ✅

**Ejemplo - Rol Básico:**

- Role ID: `987654321098765432`
- Role Name: `Básico`
- Daily Limit: `10`
- Monthly Limit: `300`
- Max Context Messages: `20`
- Priority: `5`
- Is Active: ✅

### 5. Indexar Datos de Entrenamiento (RAG)

```bash
# Ver qué se indexará
python manage.py index_training_data --dry-run

# Indexar todos los archivos
python manage.py index_training_data --clear
```

Esto procesará todos los archivos `.txt` en `discord/chatbot_ai/ai-training/` y los indexará en la base de datos.

### 6. Configurar System Prompt (Opcional)

Ir a: **Chatbot AI → Chatbot Configurations**

Buscar o crear `system_prompt` con el comportamiento deseado del bot.

---

## 🛒 Configuración de Hotmart (Opcional)

### 1. Configurar Productos

Ir a: **Invitation Roles → Hotmart Products → Add**

Crear productos:

| Campo           | Valor                | Descripción                    |
| --------------- | -------------------- | ------------------------------ |
| Product ID      | `788921`             | ID del producto en Hotmart     |
| Product name    | `Curso Premium IMAX` | Nombre descriptivo             |
| Discord role ID | `1234567890`         | ID del rol en Discord          |
| Is subscription | ✅                   | Si es suscripción recurrente   |
| Is active       | ✅                   | Si está activo                 |
| Priority        | `10`                 | Prioridad (mayor = mejor plan) |

### 2. Configurar Webhook en Hotmart

1. Ve al panel de Hotmart
2. Configuración → Webhooks
3. URL: `https://tu-dominio.com/invitation_roles/hotmart/webhook/`
4. Eventos a escuchar:
   - ✅ PURCHASE_APPROVED
   - ✅ PURCHASE_COMPLETE
   - ✅ PURCHASE_REFUNDED
   - ✅ SUBSCRIPTION_CANCELLATION
   - ✅ SWITCH_PLAN

---

## 🚀 Primera Ejecución

### 1. Verificar Configuración

```bash
# Verificar variables de entorno
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('DISCORD_BOT_TOKEN:', '✅' if os.getenv('DISCORD_BOT_TOKEN') else '❌'); print('OPENAI_API_KEY:', '✅' if os.getenv('OPENAI_API_KEY') else '❌')"
```

### 2. Iniciar el Bot

```bash
# Desde la raíz del proyecto
python bot.py
```

Deberías ver:

```
Bot listo como TuBot#1234!
✅ Chatbot de IA configurado correctamente
```

### 3. Verificar en Discord

1. El bot debe aparecer como "En línea" en tu servidor
2. Debe responder a comandos como `!ai_help`
3. Debe enviar el mensaje fijo en el canal del chatbot

---

## ✅ Verificación

### Checklist de Verificación

- [ ] Bot conectado a Discord
- [ ] Bot aparece como "En línea"
- [ ] Django Admin accesible en `http://127.0.0.1:8000/admin/`
- [ ] Base de datos conectada (sin errores en logs)
- [ ] Chunks de conocimiento indexados (RAG)
- [ ] Roles del chatbot configurados
- [ ] Comandos del bot funcionando (`!ai_help`, `!ai_stats`)
- [ ] Chatbot responde en el canal configurado
- [ ] Archivos estáticos se sirven correctamente

### Comandos de Verificación

```bash
# Verificar chunks indexados
cd discord
python manage.py shell
>>> from chatbot_ai.models import ChatbotKnowledgeChunk
>>> ChatbotKnowledgeChunk.objects.count()  # Debe ser > 0

# Verificar configuraciones
>>> from invitation_roles.models import BotConfiguration
>>> BotConfiguration.objects.filter(is_active=True).count()  # Debe ser > 0

# Verificar roles del chatbot
>>> from chatbot_ai.models import ChatbotRole
>>> ChatbotRole.objects.filter(is_active=True).count()  # Debe ser > 0
```

### Probar Chatbot

1. Ve al canal configurado del chatbot
2. Escribe una pregunta: "¿Cómo hago una restauración?"
3. El bot debe responder con información relevante
4. Verifica que use contexto RAG (debe mencionar información de IMAX)

---

## 🔧 Troubleshooting Inicial

### Bot no conecta

**Problema:** `401 Unauthorized`

**Solución:**

1. Verifica que `DISCORD_BOT_TOKEN` esté correcto
2. Verifica que el token no haya expirado
3. Regenera el token en Discord Developer Portal

### Error de base de datos

**Problema:** `connection refused` o `extension vector not found`

**Solución:**

1. Verifica que PostgreSQL esté corriendo
2. Verifica variables de entorno de PostgreSQL
3. Ejecuta: `CREATE EXTENSION IF NOT EXISTS vector;`

### No se indexan datos

**Problema:** `ChatbotKnowledgeChunk.objects.count() == 0`

**Solución:**

1. Verifica que existan archivos en `discord/chatbot_ai/ai-training/`
2. Verifica que `OPENAI_API_KEY` esté configurada
3. Ejecuta: `python manage.py index_training_data --clear`

### Chatbot no responde

**Problema:** Bot no responde en el canal

**Solución:**

1. Verifica que `chatbot_channel_id` esté configurado
2. Verifica que el bot tenga permisos en el canal
3. Verifica que el usuario tenga un rol configurado
4. Revisa logs del bot para errores

---

## 📚 Próximos Pasos

Después de la configuración inicial:

1. **Personalizar prompts**: Ajusta el system prompt según tus necesidades
2. **Agregar más datos**: Añade más archivos de entrenamiento a `ai-training/`
3. **Configurar límites**: Ajusta límites de uso según tu presupuesto
4. **Configurar Hotmart**: Si usas Hotmart, configura productos y webhook
5. **Desplegar en producción**: Sigue la guía en [DEPLOYMENT.md](./DEPLOYMENT.md)

---

**Última actualización**: Enero 2025  
**Versión**: 2.0.0
