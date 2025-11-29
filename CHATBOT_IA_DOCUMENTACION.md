# 🤖 Chatbot de IA para Discord - Documentación Completa

Sistema de chatbot inteligente integrado en Discord, especializado en odontología y la comunidad IMAX.

## 📋 Tabla de Contenidos

1. [Características Principales](#-características-principales)
2. [Arquitectura del Sistema](#-arquitectura-del-sistema)
3. [Proveedores de IA](#-proveedores-de-ia)
4. [Instalación y Configuración](#-instalación-y-configuración)
5. [Configuración desde Admin](#-configuración-desde-admin)
6. [Uso del Chatbot](#-uso-del-chatbot)
7. [Comandos Disponibles](#-comandos-disponibles)
8. [Gestión de Roles](#-gestión-de-roles)
   - [Rol por Defecto](#rol-por-defecto-default_chatbot_role_id)
9. [Base de Datos](#-base-de-datos)
10. [Troubleshooting](#-troubleshooting)
11. [API Reference](#-api-reference)

---

## 🎯 Características Principales

### ✅ **Funcionalidades Core**

- **Chat inteligente** con IA especializada en odontología
- **Contexto de conversación** (memoria de mensajes anteriores)
- **Control de acceso por roles** de Discord
- **Límites de uso** (diario/mensual por rol)
- **OpenAI** como proveedor de IA
- **Entrenamiento personalizado** con conocimiento específico
- **Estadísticas de uso** por usuario
- **Sesiones automáticas** con expiración

### 🎭 **Control de Acceso**

- **Roles específicos** con límites personalizados
- **Verificación automática** de permisos
- **Sistema de prioridades** para roles
- **Rol por defecto** para usuarios sin rol específico

### 🧠 **Inteligencia Artificial**

- **Especialización médica** en odontología
- **Prompts del sistema** personalizables
- **Base de conocimiento** específica de IMAX
- **Ejemplos de conversación** para entrenamiento
- **Reglas de seguridad** médica integradas

---

## 🏗️ Arquitectura del Sistema

### **Estructura Modular**

```
discord/
├── invitation_roles/          # App original (Hotmart, roles, invites)
├── chatbot_ai/               # Nueva app del chatbot
│   ├── models.py             # Modelos de base de datos
│   ├── ai_service.py         # Servicio de IA
│   ├── chatbot_service.py    # Lógica de negocio
│   ├── discord_commands.py   # Comandos de Discord
│   ├── admin.py              # Admin de Django
│   └── management/           # Comandos de gestión
└── discord/                  # Configuración Django
    └── settings.py           # Configuración
```

### **Flujo de Datos**

```
Usuario Discord → Discord Commands → Chatbot Service → AI Service → API Provider
                     ↓                    ↓              ↓
                Verificación          Gestión        Generación
                de Permisos          de Sesión       de Respuesta
```

---

## 🤖 Proveedor de IA

### **OpenAI**

- **Modelo por defecto**: `gpt-4o-mini`
- **Modelos disponibles**: `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`
- **API Key**: Configurar en `.env` como `OPENAI_API_KEY`
- **Calidad**: ⭐⭐⭐⭐⭐ Excelente
- **Costo**: 💰 Pago por uso (muy económico con gpt-4o-mini)

---

## 🚀 Instalación y Configuración

### **1. Requisitos Previos**

```bash
# Python 3.10+
# Django 5.2+
# PostgreSQL
# Discord Bot Token
```

### **2. Instalación de Dependencias**

```bash
pip install discord.py django asgiref aiohttp
```

### **3. Configuración Inicial**

```bash
# Navegar al directorio Django
cd discord

# Activar entorno virtual
source ../venv/bin/activate  # Linux/Mac
# o
..\venv\Scripts\activate     # Windows

# Aplicar migraciones
python manage.py migrate

# Configurar chatbot
python manage.py setup_chatbot
```

### **4. Variables de Entorno**

```bash
# .env file
DISCORD_BOT_TOKEN=tu_token_aqui
OPENAI_API_KEY=sk-proj-...

# Base de datos (si usas Docker con pgvector)
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DATABASE=django_discord_bot
```

---

## ⚙️ Configuración desde Admin

### **Acceso al Admin**

```
http://127.0.0.1:8000/
```

_Redirige automáticamente al admin de Django_

### **Configuraciones del Bot**

#### **Configuraciones Principales:**

| Nombre                    | Tipo    | Descripción                                                                        | Ejemplo              |
| ------------------------- | ------- | ---------------------------------------------------------------------------------- | -------------------- |
| `chatbot_channel_id`      | channel | ID del canal donde funciona el bot                                                 | `123456789012345678` |
| `default_chatbot_role_id` | general | Rol por defecto para usuarios sin rol específico (ver sección de gestión de roles) | `987654321098765432` |
| `openai_model`            | general | Modelo de OpenAI a usar                                                            | `gpt-4o-mini`        |

**Nota**: La API key de OpenAI se configura en el archivo `.env` como `OPENAI_API_KEY`.

#### **Configuración del Sistema:**

| Nombre                       | Tipo     | Descripción                            |
| ---------------------------- | -------- | -------------------------------------- |
| `system_prompt`              | general  | Prompt del sistema para la IA          |
| `Ejemplos de Procedimientos` | training | Ejemplos de conversaciones             |
| `Base de Conocimiento IMAX`  | training | Información específica de la comunidad |

### **Roles del Chatbot**

#### **Configuración de Roles:**

| Campo                  | Descripción                       | Ejemplo                    |
| ---------------------- | --------------------------------- | -------------------------- |
| `role_id`              | ID del rol de Discord             | `123456789012345678`       |
| `role_name`            | Nombre del rol                    | `VIP`, `Premium`, `Básico` |
| `daily_limit`          | Límite diario de mensajes         | `50`                       |
| `monthly_limit`        | Límite mensual de mensajes        | `1000`                     |
| `max_context_messages` | Máximo de mensajes en contexto    | `30`                       |
| `priority`             | Prioridad del rol (mayor = mejor) | `10`                       |

#### **Roles Predefinidos:**

- **VIP**: 50 mensajes/día, 1000/mes, contexto: 30
- **Premium**: 30 mensajes/día, 600/mes, contexto: 25
- **Básico**: 10 mensajes/día, 300/mes, contexto: 20

---

## 💬 Uso del Chatbot

### **Activación del Bot**

1. **Canal configurado**: El bot responde automáticamente solo en el canal configurado específicamente
2. **Permisos**: El usuario debe tener un rol configurado con acceso
3. **Mensaje fijo**: Se envía automáticamente al iniciar el bot (permanece fijo en el canal)
4. **Mensaje de bienvenida**: Se muestra automáticamente en la primera interacción (se auto-elimina en 30 segundos)

### **Interacción**

```
Usuario: "¿Cómo hago una restauración con composite?"
Bot: "🤖 Para una restauración con composite, sigue estos pasos..."
```

### **Características de la Conversación**

- **Contexto**: Recuerda mensajes anteriores en la sesión
- **Especialización**: Responde sobre odontología y procedimientos
- **Seguridad**: No da diagnósticos médicos específicos
- **Tono**: Profesional pero accesible
- **Mensaje fijo**: Se envía automáticamente al iniciar el bot
- **Mensaje de bienvenida**: Se muestra automáticamente en la primera interacción del usuario

### **Mensaje de Bienvenida Automático**

Cuando un usuario interactúa por primera vez con el chatbot en un canal, recibe automáticamente un mensaje de bienvenida que incluye:

- 📝 **Uso rápido**: Instrucciones básicas con ejemplos
- 🎭 **Límites por rol**: Información sobre límites diarios/mensuales
- ⚠️ **Recordatorios importantes**: Sobre consulta profesional y reglas
- 💡 **Comandos disponibles**: Referencia a `!ai_help` para ayuda completa

**Características del mensaje:**

- Se muestra solo en la primera interacción
- Se auto-elimina después de 30 segundos
- No interfiere con la conversación normal

---

## ⚡ Comandos Disponibles

### **Comandos de Usuario**

| Comando     | Descripción                             | Ejemplo     |
| ----------- | --------------------------------------- | ----------- |
| `!ai_stats` | Muestra estadísticas de uso del usuario | `!ai_stats` |
| `!ai_help`  | Muestra ayuda completa del chatbot      | `!ai_help`  |
| `!ai_info`  | Muestra información básica y uso rápido | `!ai_info`  |

### **Comandos de Administrador**

| Comando       | Descripción                         | Permisos      |
| ------------- | ----------------------------------- | ------------- |
| `!ai_pin`     | Envía y fija mensaje de información | Administrator |
| `!ai_cleanup` | Limpia sesiones expiradas           | Administrator |
| `!ai_roles`   | Muestra roles configurados          | Administrator |

### **Comandos de Django**

```bash
# Configurar chatbot
python manage.py setup_chatbot

# Crear superusuario
python manage.py createsuperuser

# Aplicar migraciones
python manage.py migrate
```

---

## 🎭 Gestión de Roles

### **Sistema de Prioridades**

Los roles se evalúan por prioridad (mayor número = mayor prioridad):

```
VIP (prioridad: 10)     → Mejor acceso
Premium (prioridad: 8)  → Acceso medio
Básico (prioridad: 5)   → Acceso básico
```

### **Verificación de Acceso**

1. **Obtener roles del usuario** en Discord
2. **Buscar rol configurado** con mayor prioridad
3. **Verificar límites** diarios y mensuales
4. **Permitir o denegar** acceso

### **Límites de Uso**

- **Diario**: Se resetea cada día a medianoche
- **Mensual**: Se resetea cada mes
- **Contexto**: Máximo de mensajes recordados por sesión

### **Rol por Defecto (default_chatbot_role_id)**

El `default_chatbot_role_id` es el **rol de respaldo** que se asigna automáticamente a usuarios que **NO tienen ningún rol configurado** para el chatbot.

#### **Cómo Funciona:**

1. **Verificación de roles**: El bot busca si el usuario tiene algún rol configurado en el chatbot
2. **Si encuentra rol**: Usa los límites de ese rol específico
3. **Si NO encuentra rol**: Usa el `default_chatbot_role_id`

#### **Casos de Uso:**

**✅ Usuario CON rol configurado:**

```
Usuario tiene rol "VIP" → Usa límites de VIP (50 mensajes/día)
Usuario tiene rol "Premium" → Usa límites de Premium (30 mensajes/día)
Usuario tiene rol "Básico" → Usa límites de Básico (10 mensajes/día)
```

**❌ Usuario SIN rol configurado:**

```
Usuario no tiene rol configurado → Usa default_chatbot_role_id
```

#### **Configuraciones Recomendadas:**

| Tipo de Comunidad | Configuración                                | Resultado                             |
| ----------------- | -------------------------------------------- | ------------------------------------- |
| **Abierta**       | `default_chatbot_role_id = "ID_rol_Básico"`  | Todos pueden usar con límites básicos |
| **Restringida**   | `default_chatbot_role_id = ""` (vacío)       | Solo usuarios con roles específicos   |
| **Premium**       | `default_chatbot_role_id = "ID_rol_Premium"` | Todos reciben acceso premium          |

#### **Ejemplo Práctico:**

```python
# Flujo de verificación de roles
user_roles = sorted(member.roles, key=lambda r: r.position, reverse=True)

# Buscar rol configurado
for role in user_roles:
    chatbot_role = ChatbotRole.objects.filter(role_id=str(role.id), is_active=True).first()
    if chatbot_role:
        return str(role.id)  # ✅ Usuario tiene rol configurado

# Si no encuentra ningún rol configurado...
default_role_id = await self._get_bot_config('default_chatbot_role_id')
return default_role_id or ""  # 🔄 Usa rol por defecto
```

#### **Configuración Paso a Paso:**

1. **Crear rol en Discord:**

   - Configuración del servidor → Roles
   - Crear rol "Básico" (o el que prefieras)
   - Copiar el ID del rol

2. **Configurar en Admin:**

   - Ir a `http://127.0.0.1:8000/admin/`
   - Buscar "Configuraciones del Bot"
   - Editar `default_chatbot_role_id`
   - Pegar el ID del rol

3. **Configurar límites del rol:**
   - Ir a "Roles Chatbot"
   - Crear/editar el rol por defecto
   - Configurar límites deseados

#### **Recomendación para IMAX:**

```
default_chatbot_role_id = "ID_del_rol_Básico"
```

- **Ventajas**: Todos pueden participar, control de costos, usuarios premium pueden tener roles específicos
- **Límites sugeridos**: 10 mensajes/día, 300/mes

---

## 🗄️ Base de Datos

### **Modelos Principales**

#### **ChatbotConfiguration**

```python
name: str           # Nombre de la configuración
value: str          # Valor de la configuración
description: str    # Descripción
is_active: bool     # Si está activa
```

#### **ChatbotRole**

```python
role_id: str              # ID del rol de Discord
role_name: str            # Nombre del rol
daily_limit: int          # Límite diario
monthly_limit: int        # Límite mensual
max_context_messages: int # Máximo contexto
priority: int             # Prioridad
is_active: bool           # Si está activo
```

#### **ChatbotSession**

```python
user_id: str          # ID del usuario
username: str         # Nombre de usuario
channel_id: str       # ID del canal
role_id: str          # ID del rol
is_active: bool       # Si está activa
expires_at: datetime  # Cuándo expira
```

#### **ChatbotMessage**

```python
session: ChatbotSession    # Sesión relacionada
message_id: str            # ID del mensaje
user_message: str          # Mensaje del usuario
ai_response: str           # Respuesta de la IA
tokens_used: int           # Tokens consumidos
processing_time: float     # Tiempo de procesamiento
```

#### **ChatbotUsage**

```python
user_id: str         # ID del usuario
role_id: str         # ID del rol
date: date           # Fecha del uso
daily_count: int     # Contador diario
monthly_count: int   # Contador mensual
```

#### **ChatbotTraining**

```python
name: str                    # Nombre del entrenamiento
training_type: str           # Tipo (system_prompt, knowledge_base, etc.)
content: str                 # Contenido del entrenamiento
priority: int                # Prioridad
is_active: bool              # Si está activo
```

---

## 🔧 Troubleshooting

### **Problemas Comunes**

#### **Bot no responde**

1. **Verificar canal**: ¿Está configurado `chatbot_channel_id`?
2. **Verificar permisos**: ¿El usuario tiene rol configurado?
3. **Verificar límites**: ¿Ha alcanzado límites diarios/mensuales?
4. **Verificar API**: ¿Está configurada la API key?

#### **Error de API**

1. **Verificar API key**: ¿Es válida y tiene créditos?
2. **Verificar proveedor**: ¿Está configurado `ai_provider`?
3. **Verificar internet**: ¿Hay conexión a internet?

#### **Error de base de datos**

1. **Verificar migraciones**: `python manage.py migrate`
2. **Verificar configuración**: `python manage.py setup_chatbot`
3. **Verificar permisos**: ¿Django puede escribir en la DB?

### **Logs y Debugging**

```python
# Habilitar logs detallados
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 📚 API Reference

### **AIService**

```python
class AIService:
    async def generate_response(
        self,
        user_message: str,
        session: ChatbotSession,
        provider: str | None = None
    ) -> Tuple[str, int, float]:
        """
        Genera respuesta de la IA

        Args:
            user_message: Mensaje del usuario
            session: Sesión de chat activa
            provider: Proveedor específico (opcional)

        Returns:
            Tuple[str, int, float]: (respuesta, tokens_usados, tiempo_procesamiento)
        """
```

### **ChatbotService**

```python
class ChatbotService:
    async def can_user_use_chatbot(
        self,
        user_id: str,
        role_id: str
    ) -> Tuple[bool, str]:
        """
        Verifica si un usuario puede usar el chatbot

        Args:
            user_id: ID del usuario de Discord
            role_id: ID del rol del usuario

        Returns:
            Tuple[bool, str]: (puede_usar, mensaje_error)
        """
```

### **Comandos Discord**

```python
class ChatbotCog(commands.Cog):
    @commands.command(name='ai_stats')
    async def ai_stats(self, ctx):
        """Muestra estadísticas de uso del chatbot"""

    @commands.command(name='ai_help')
    async def ai_help(self, ctx):
        """Muestra ayuda del chatbot"""
```

---

## 🚀 Despliegue

### **Producción**

1. **Configurar variables de entorno** en el servidor
2. **Usar PostgreSQL** en lugar de SQLite
3. **Configurar HTTPS** para el admin
4. **Configurar logging** apropiado
5. **Usar supervisor** o similar para mantener el bot activo

### **Monitoreo**

- **Logs del bot**: Errores y actividad
- **Uso de API**: Tokens consumidos y costos
- **Estadísticas**: Usuarios activos y mensajes procesados

---

## 📞 Soporte

### **Documentación Adicional**

- [Guía de Hotmart Integration](HOTMART_INTEGRATION.md)
- [Guía del Chatbot IA](CHATBOT_IA_GUIA.md)

### **Contacto**

Para soporte técnico o preguntas sobre la implementación, contacta al equipo de desarrollo.

---

**Última actualización**: Enero 2025  
**Versión**: 2.0.0  
**Compatibilidad**: Discord.py 2.3+, Django 5.2+
