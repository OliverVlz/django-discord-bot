# 🤖 Chatbot Inteligente con IA - Guía Completa

Sistema de chatbot con inteligencia artificial integrado en Discord para la comunidad IMAX.

> **📁 Estructura Modular**: El chatbot ahora está separado en su propia app Django (`chatbot_ai`) para mejor organización y mantenimiento.

## 🎯 Características Principales

### ✅ **Funcionalidades**

- 🤖 **Asistente IA especializado** en odontología
- 🎭 **Control de acceso por roles** con límites personalizables
- 💾 **Memoria de contexto** con límites configurables
- 📊 **Sistema de límites** diarios y mensuales por rol
- 🧠 **Entrenamiento personalizado** con base de conocimiento
- 📈 **Estadísticas de uso** en tiempo real
- 🔄 **Sesiones persistentes** con expiración automática

### 🏗️ **Arquitectura**

- **Canal público**: Conversaciones visibles para todos (recomendado)
- **Memoria contextual**: Mantiene contexto de conversación
- **Rate limiting**: Límites por rol para control de costos
- **Múltiples proveedores**: OpenAI GPT-4 y Anthropic Claude

---

## 🚀 Instalación y Configuración

### 1. **Variables de Entorno**

Agregar a tu archivo `.env`:

```bash
# Proveedor de IA (openai o anthropic)
AI_PROVIDER=openai

# OpenAI (si usas GPT-4)
OPENAI_API_KEY=sk-...

# Anthropic (si usas Claude)
ANTHROPIC_API_KEY=sk-ant-...

# Discord (ya configurado)
DISCORD_BOT_TOKEN=tu_token_aqui
```

### 2. **Ejecutar Configuración Inicial**

```bash
python setup_chatbot.py
```

### 3. **Aplicar Migraciones**

```bash
python manage.py migrate
```

> **ℹ️ Nota**: Las migraciones del chatbot se encuentran en `chatbot_ai/migrations/`

### 4. **Configurar en Admin de Django**

#### **Bot Configurations:**

- `chatbot_channel_id`: ID del canal donde funcionará el bot
- `default_chatbot_role_id`: Rol por defecto para usuarios sin rol específico
- `ai_provider`: Proveedor de IA (openai/anthropic)

#### **Chatbot Roles:**

Configurar roles con sus límites:

- `daily_limit`: Mensajes por día
- `monthly_limit`: Mensajes por mes
- `max_context_messages`: Mensajes en memoria
- `priority`: Prioridad del rol (mayor = mejor)

### 5. **Reiniciar el Bot**

```bash
python bot.py
```

---

## 🎛️ Configuración de Roles

### **Ejemplo de Configuración:**

| Rol     | Diario | Mensual | Contexto | Prioridad |
| ------- | ------ | ------- | -------- | --------- |
| VIP     | 50     | 1000    | 30       | 10        |
| Premium | 30     | 600     | 25       | 8         |
| Básico  | 10     | 300     | 20       | 5         |

### **Cómo Funciona:**

1. El bot detecta automáticamente el rol más alto del usuario
2. Aplica los límites correspondientes
3. Mantiene contexto según el límite configurado
4. Resetea contadores diarios automáticamente

---

## 💬 Uso del Chatbot

### **Para Usuarios:**

1. **Escribir en el canal**: Simplemente escribe tu pregunta
2. **El bot responde**: Automáticamente con información especializada
3. **Ver estadísticas**: Usa `!ai_stats` para ver tu uso
4. **Obtener ayuda**: Usa `!ai_help` para información

### **Comandos Disponibles:**

- `!ai_help` - Ayuda del chatbot
- `!ai_stats` - Estadísticas de uso personal
- `!ai_roles` - Ver roles configurados (admins)
- `!ai_cleanup` - Limpiar sesiones expiradas (admins)

### **Ejemplo de Conversación:**

```
Usuario: ¿Cómo hago una endodoncia en un molar?
🤖 Bot: Para una endodoncia en molar, sigue estos pasos:

1. **Diagnóstico**: Radiografía y pruebas de vitalidad
2. **Aislamiento**: Campo operatorio absoluto
3. **Acceso**: Preparación de cavidad de acceso
4. **Instrumentación**: Limpieza y conformación de conductos
5. **Obturación**: Sellado hermético con gutapercha
6. **Restauración**: Reconstrucción coronaria

⚠️ Siempre consulta con un endodoncista para casos complejos.
```

---

## 🧠 Entrenamiento Personalizado

### **Tipos de Entrenamiento:**

1. **System Prompt**: Comportamiento base del bot
2. **Knowledge Base**: Información específica de IMAX
3. **Examples**: Ejemplos de conversaciones
4. **Rules**: Reglas específicas del dominio

### **Agregar Entrenamiento:**

En el admin de Django → **Chatbot Training**:

```json
{
  "name": "Protocolos de Emergencia",
  "training_type": "knowledge_base",
  "content": "En emergencias odontológicas...",
  "priority": 10
}
```

### **Prioridades:**

- **10**: Información crítica
- **8**: Información importante
- **5**: Información general
- **1**: Información básica

---

## 📊 Monitoreo y Estadísticas

### **Métricas Disponibles:**

- **Uso por usuario**: Mensajes diarios/mensuales
- **Tokens consumidos**: Costo de API
- **Tiempo de respuesta**: Performance del sistema
- **Sesiones activas**: Usuarios conectados

### **Limpieza Automática:**

- **Sesiones**: Expiran en 24 horas
- **Contexto**: Se limpia automáticamente
- **Estadísticas**: Se mantienen por 90 días

---

## 🔧 Administración

### **Panel de Admin Django:**

#### **Chatbot Sessions:**

- Ver sesiones activas
- Monitorear actividad
- Limpiar sesiones manualmente

#### **Chatbot Messages:**

- Historial de conversaciones
- Análisis de tokens usados
- Tiempo de procesamiento

#### **Chatbot Usage:**

- Estadísticas de uso por usuario
- Contadores diarios/mensuales
- Análisis de patrones

### **Comandos de Administración:**

```bash
# Limpiar sesiones expiradas
!ai_cleanup

# Ver roles configurados
!ai_roles

# Ver estadísticas generales (en admin)
```

---

## 🛡️ Seguridad y Límites

### **Control de Acceso:**

- ✅ Solo roles configurados pueden usar el bot
- ✅ Límites diarios y mensuales por rol
- ✅ Contexto limitado para evitar costos excesivos
- ✅ Sesiones con expiración automática

### **Prevención de Abuso:**

- 🚫 Límites estrictos por rol
- 🚫 Expiración de sesiones
- 🚫 Validación de permisos en cada mensaje
- 🚫 Rate limiting automático

### **Privacidad:**

- 🔒 Conversaciones en canal público (transparente)
- 🔒 No almacena información personal
- 🔒 Tokens se limpian automáticamente
- 🔒 Sesiones expiran automáticamente

---

## 💰 Control de Costos

### **Optimizaciones:**

1. **Límites por rol**: Controla el uso según el nivel
2. **Contexto limitado**: Reduce tokens por conversación
3. **Sesiones cortas**: Expira en 24 horas
4. **Limpieza automática**: Reduce almacenamiento

### **Monitoreo de Costos:**

- **Tokens por mensaje**: Registrado en cada respuesta
- **Uso por usuario**: Estadísticas detalladas
- **Límites configurables**: Ajusta según presupuesto

---

## 🚨 Troubleshooting

### **Problemas Comunes:**

#### **Bot no responde:**

1. Verificar que el canal esté configurado
2. Verificar permisos del usuario
3. Verificar límites de uso
4. Verificar API key de IA

#### **Error de API:**

1. Verificar API key válida
2. Verificar límites de API
3. Verificar conectividad
4. Revisar logs del sistema

#### **Límites no funcionan:**

1. Verificar configuración de roles
2. Verificar que el usuario tenga rol
3. Verificar configuración en admin
4. Reiniciar bot

### **Logs y Debugging:**

```bash
# Ver logs del bot
tail -f bot.log

# Ver logs de Django
python manage.py shell
>>> from invitation_roles.models_chatbot import ChatbotSession
>>> ChatbotSession.objects.filter(is_active=True).count()
```

---

## 📈 Mejoras Futuras

### **Funcionalidades Planificadas:**

- 🎨 **Interfaz web** para administración
- 📊 **Dashboard** con métricas en tiempo real
- 🔄 **Integración** con más proveedores de IA
- 🎯 **Análisis de sentimientos** de conversaciones
- 📱 **Notificaciones** push para admins
- 🔍 **Búsqueda** en historial de conversaciones

### **Optimizaciones:**

- ⚡ **Cache** de respuestas frecuentes
- 🧠 **Aprendizaje** de patrones de uso
- 📊 **A/B testing** de prompts
- 🔄 **Auto-tuning** de límites

---

## 📞 Soporte

### **Recursos:**

- 📖 **Documentación**: Este archivo
- 🐛 **Issues**: Reportar en el repositorio
- 💬 **Comunidad**: Canal de Discord
- 📧 **Contacto**: Admin del servidor

### **Mantenimiento:**

- 🔄 **Actualizaciones**: Mensuales
- 🧹 **Limpieza**: Automática
- 📊 **Backup**: Diario
- 🔒 **Seguridad**: Revisión continua

---

¡El chatbot de IA está listo para mejorar la experiencia de la comunidad IMAX! 🚀
