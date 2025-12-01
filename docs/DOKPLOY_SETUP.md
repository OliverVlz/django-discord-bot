# 🚀 Configuración para Dokploy

## ¿Qué es Dokploy?

Dokploy es una plataforma de despliegue autoalojable (similar a Heroku/Vercel) que:
- Soporta Dockerfiles
- Gestiona bases de datos PostgreSQL automáticamente
- Tiene interfaz web para configurar todo
- Monitorea tus aplicaciones

## 📋 Pasos para Desplegar en Dokploy

### 1. Preparar el Repositorio

Asegúrate de tener estos archivos en tu repo:
- ✅ `Dockerfile` (ya creado)
- ✅ `supervisord.conf` (ya creado)
- ✅ `requirements.txt`
- ✅ `.env.example` (opcional, para referencia)

### 2. En Dokploy - Crear Nueva Aplicación

1. **Conectar Repositorio:**
   - Ve a "Applications" → "New Application"
   - Conecta tu repositorio de GitHub/GitLab
   - Selecciona la rama `main` (o la que uses)

2. **Configurar Build:**
   - **Build Type**: `Dockerfile`
   - **Dockerfile Path**: `Dockerfile` (raíz del proyecto)
   - **Build Context**: `.` (raíz)

3. **Configurar Puerto:**
   - **Port**: `8000` (para Django Admin)

### 3. Variables de Entorno

En la sección "Environment Variables" de Dokploy, agrega:

```env
# Discord
DISCORD_BOT_TOKEN=tu_token_aqui

# OpenAI
OPENAI_API_KEY=sk-proj-...

# PostgreSQL (Dokploy te dará estos valores automáticamente)
POSTGRES_HOST=<dokploy_te_da_esto>
POSTGRES_PORT=5432
POSTGRES_USER=<dokploy_te_da_esto>
POSTGRES_PASSWORD=<dokploy_te_da_esto>
POSTGRES_DATABASE=<dokploy_te_da_esto>
```

**Nota**: Dokploy puede crear la base de datos automáticamente. Cuando la crees, te dará las variables de conexión.

### 4. Crear Base de Datos PostgreSQL

1. En Dokploy, ve a "Databases" → "New Database"
2. Selecciona **PostgreSQL**
3. Dokploy te dará automáticamente:
   - `POSTGRES_HOST`
   - `POSTGRES_USER`
   - `POSTGRES_PASSWORD`
   - `POSTGRES_DATABASE`
4. Copia estos valores a las variables de entorno de tu aplicación

### 5. Ejecutar Migraciones (Primera vez)

Después del primer deploy, necesitas ejecutar migraciones:

**Opción A: Desde la terminal de Dokploy**
```bash
python discord/manage.py migrate
python discord/manage.py createsuperuser
```

**Opción B: Desde tu máquina local**
```bash
# Conectarte al contenedor y ejecutar
docker exec -it <container_id> python discord/manage.py migrate
```

### 6. Configurar el Chatbot

Una vez que Django Admin esté corriendo:

1. Accede a: `https://tu-dominio.dokploy.com/admin/`
2. Crea superusuario si no lo hiciste
3. Configura:
   - Roles del chatbot
   - System prompt
   - Entrenamientos

## 🔧 ¿Cómo Funciona el Dockerfile?

```
1. Usa Python 3.12 como base
2. Instala supervisor (para correr 2 procesos)
3. Instala dependencias de requirements.txt
4. Copia todo el código
5. Configura supervisor para correr:
   - Django en puerto 8000
   - Bot de Discord
6. Si alguno se cae, supervisor lo reinicia automáticamente
```

## 📝 ¿Qué es supervisord.conf?

Es la configuración de **Supervisor**, un programa que:
- ✅ Corre múltiples procesos en un contenedor
- ✅ Reinicia procesos si se caen
- ✅ Muestra logs de ambos procesos

**Estructura:**
```ini
[program:django]        ← Proceso 1: Django Admin
command=python discord/manage.py runserver 0.0.0.0:8000
autorestart=true        ← Si muere, lo reinicia

[program:discord_bot]   ← Proceso 2: Bot de Discord
command=python bot.py
autorestart=true        ← Si muere, lo reinicia
```

## 🐛 Troubleshooting

### El bot no conecta a Discord
- Verifica `DISCORD_BOT_TOKEN` en variables de entorno
- Revisa logs en Dokploy

### Django Admin no carga
- Verifica que el puerto 8000 esté expuesto
- Revisa logs de Django en Dokploy

### Error de base de datos
- Verifica variables de PostgreSQL
- Asegúrate de que la BD esté creada en Dokploy
- Ejecuta migraciones: `python discord/manage.py migrate`

### Ver logs
En Dokploy, ve a tu aplicación → "Logs" para ver:
- Logs de Django
- Logs del Bot
- Errores de supervisor

## 🎯 Resumen

1. **Dokploy** → Plataforma de despliegue
2. **Dockerfile** → Instrucciones para construir tu app
3. **supervisord.conf** → Corre Django + Bot juntos
4. **Variables de entorno** → Configuración (tokens, BD, etc.)
5. **PostgreSQL** → Base de datos gestionada por Dokploy

¡Listo para desplegar! 🚀



