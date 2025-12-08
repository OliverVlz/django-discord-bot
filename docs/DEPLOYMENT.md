# 🚀 Guía de Despliegue en Producción

Guía completa para desplegar el bot de Discord en producción usando Docker, Nginx y Dokploy.

## 📋 Tabla de Contenidos

1. [Arquitectura de Producción](#-arquitectura-de-producción)
2. [Despliegue con Docker](#-despliegue-con-docker)
3. [Despliegue en Dokploy](#-despliegue-en-dokploy)
4. [Configuración de Nginx](#-configuración-de-nginx)
5. [Variables de Entorno](#-variables-de-entorno)
6. [Troubleshooting](#-troubleshooting)

---

## 🏗️ Arquitectura de Producción

### Componentes

```
┌─────────────────────────────────────────────────────────┐
│                    Nginx (Puerto 8000)                  │
│  • Servidor web público                                 │
│  • Proxy reverso a Django                              │
│  • Sirve archivos estáticos                            │
└───────────────┬─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────┐
│              Supervisor (Proceso Principal)            │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │ Django/Gunicorn  │  │  Discord Bot     │            │
│  │ (Puerto 8001)    │  │  (Proceso)       │            │
│  └──────────────────┘  └──────────────────┘            │
└───────────────┬─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────┐
│         PostgreSQL + pgvector                           │
│  • Base de datos principal                              │
│  • Almacenamiento de vectores                           │
└─────────────────────────────────────────────────────────┘
```

### Flujo de Peticiones

1. **Cliente** → Nginx (puerto 8000)
2. **Nginx** → Gunicorn/Django (puerto 8001 interno)
3. **Django** → PostgreSQL
4. **Bot Discord** → Corre como proceso separado

---

## 🐳 Despliegue con Docker

### 1. Estructura del Dockerfile

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    supervisor \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Recolectar archivos estáticos
RUN DJANGO_SECRET_KEY=temp-build-key python discord/manage.py collectstatic --noinput

# Copiar configuraciones
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 8000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

### 2. Docker Compose (Desarrollo Local)

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - POSTGRES_HOST=host.docker.internal
      - POSTGRES_PORT=5433
    volumes:
      - .:/app

  db:
    image: pgvector/pgvector:pg17
    ports:
      - "5433:5432"
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=django_discord_bot
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### 3. Comandos Docker

```bash
# Construir imagen
docker build -t discord-bot .

# Ejecutar contenedor
docker run -d \
  --name discord-bot \
  -p 8000:8000 \
  --env-file .env \
  discord-bot

# Ver logs
docker logs -f discord-bot

# Ejecutar comandos dentro del contenedor
docker exec -it discord-bot python discord/manage.py migrate
docker exec -it discord-bot python discord/manage.py index_training_data --clear
```

---

## ☁️ Despliegue en Dokploy

### 1. Preparar el Repositorio

Asegúrate de tener estos archivos en tu repo:
- ✅ `Dockerfile` (en la raíz)
- ✅ `supervisord.conf` (en la raíz)
- ✅ `nginx.conf` (en la raíz)
- ✅ `requirements.txt`
- ✅ `.dockerignore` (opcional)

### 2. Crear Nueva Aplicación en Dokploy

1. **Conectar Repositorio:**
   - Ve a "Applications" → "New Application"
   - Conecta tu repositorio de GitHub/GitLab
   - Selecciona la rama `main` (o la que uses)

2. **Configurar Build:**
   - **Build Type**: `Dockerfile`
   - **Dockerfile Path**: `Dockerfile` (raíz del proyecto)
   - **Build Context**: `.` (raíz)

3. **Configurar Puerto:**
   - **Port**: `8000` (puerto público)

### 3. Variables de Entorno en Dokploy

En la sección "Environment Variables" de Dokploy, agrega:

```env
# Discord
DISCORD_BOT_TOKEN=tu_token_aqui
CLIENT_ID=tu_client_id

# OpenAI
OPENAI_API_KEY=sk-proj-...

# Django
DJANGO_SECRET_KEY=tu_secret_key_aqui
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com,*.dokploy.com
CSRF_TRUSTED_ORIGINS=https://tu-dominio.com,https://*.dokploy.com

# Base de Datos (Dokploy te dará estos valores)
POSTGRES_HOST=72.61.2.5
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres-discord-bot-2025
POSTGRES_DATABASE=discord-db

# Email (Gmail - opcional)
GMAIL_ADDRESS=tu-email@gmail.com
GMAIL_APP_PASSWORD=tu-app-password
```

**Nota sobre Gmail App Password:**
- Requiere verificación en dos pasos activada en tu cuenta de Google
- Se genera en: [Google Account](https://myaccount.google.com) → Seguridad → Contraseñas de aplicaciones
- Es una contraseña de 16 caracteres sin espacios
- Selecciona "Correo" y "Otro (personalizado)" → Escribe "Discord Bot"
```

### 4. Crear Base de Datos PostgreSQL

1. En Dokploy, ve a "Databases" → "New Database"
2. Selecciona **PostgreSQL**
3. Dokploy te dará automáticamente:
   - `POSTGRES_HOST`
   - `POSTGRES_USER`
   - `POSTGRES_PASSWORD`
   - `POSTGRES_DATABASE`
4. Copia estos valores a las variables de entorno de tu aplicación

### 5. Habilitar pgvector

Después de crear la base de datos, ejecuta:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Puedes hacerlo desde:
- La consola SQL de Dokploy
- O desde un contenedor temporal:
  ```bash
  docker exec -it <db-container> psql -U postgres -d discord-db -c "CREATE EXTENSION IF NOT EXISTS vector;"
  ```

### 6. Ejecutar Migraciones (Primera vez)

Después del primer deploy, necesitas ejecutar migraciones:

**Opción A: Desde la terminal de Dokploy**
```bash
python discord/manage.py migrate
python discord/manage.py createsuperuser
python discord/manage.py index_training_data --clear
```

**Opción B: Desde tu máquina local**
```bash
# Conectarte al contenedor y ejecutar
docker exec -it <container_id> python discord/manage.py migrate
```

### 7. Configurar el Chatbot

Una vez que Django Admin esté corriendo:

1. Accede a: `https://tu-dominio.dokploy.com/admin/`
2. Crea superusuario si no lo hiciste
3. Configura:
   - Roles del chatbot
   - System prompt
   - Productos de Hotmart
   - Configuraciones del bot

---

## 🌐 Configuración de Nginx

### Archivo nginx.conf

```nginx
worker_processes 1;

events {
    worker_connections 1024;
}

http {
    include mime.types;
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 65;

    server {
        listen 8000;
        server_name localhost;

        # Archivos estáticos
        location /static/ {
            alias /app/discord/staticfiles/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        # Proxy a Django
        location / {
            proxy_pass http://127.0.0.1:8001;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-Port $server_port;
        }
    }
}
```

### ¿Por qué Nginx?

- ✅ **Servir archivos estáticos** eficientemente
- ✅ **Proxy reverso** a Django/Gunicorn
- ✅ **Mejor rendimiento** que servir estáticos desde Django
- ✅ **Configuración de headers** para seguridad

---

## ⚙️ Configuración de Supervisor

### Archivo supervisord.conf

```ini
[supervisord]
nodaemon=true
user=root

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:django]
command=gunicorn discord.wsgi:application --bind 0.0.0.0:8001 --workers 2
directory=/app/discord
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:discord_bot]
command=python bot.py
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

### ¿Por qué Supervisor?

- ✅ **Múltiples procesos** en un solo contenedor
- ✅ **Reinicio automático** si un proceso falla
- ✅ **Logs centralizados** en stdout/stderr
- ✅ **Gestión simple** de procesos

---

## 🔐 Variables de Entorno

### Variables Requeridas

```env
# Discord (OBLIGATORIO)
DISCORD_BOT_TOKEN=tu_token_aqui

# OpenAI (OBLIGATORIO para chatbot)
OPENAI_API_KEY=sk-proj-...

# Django (OBLIGATORIO)
DJANGO_SECRET_KEY=tu_secret_key_aqui
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com,*.dokploy.com
CSRF_TRUSTED_ORIGINS=https://tu-dominio.com

# Base de Datos (OBLIGATORIO)
POSTGRES_HOST=tu-host
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=tu-password
POSTGRES_DATABASE=tu-database
```

### Variables Opcionales

```env
# Email (Gmail - opcional)
GMAIL_ADDRESS=tu-email@gmail.com
GMAIL_APP_PASSWORD=tu-app-password

# Discord (opcional)
CLIENT_ID=tu_client_id
DISCORD_NOTIFICATION_WEBHOOK=https://discord.com/api/webhooks/...

# Hotmart (opcional)
HOTMART_WEBHOOK_SECRET=tu-secret
```

---

## 🔧 Troubleshooting

### El bot no conecta a Discord

**Síntomas:**
```
Error: 401 Unauthorized
```

**Solución:**
1. Verifica `DISCORD_BOT_TOKEN` en variables de entorno
2. Asegúrate de que el token sea válido
3. Revisa logs en Dokploy: `docker logs <container_id>`

### Django Admin no carga

**Síntomas:**
```
502 Bad Gateway
```

**Solución:**
1. Verifica que Gunicorn esté corriendo:
   ```bash
   docker exec -it <container_id> supervisorctl status
   ```
2. Verifica que el puerto 8001 esté accesible internamente
3. Revisa logs de Django:
   ```bash
   docker logs <container_id> | grep django
   ```

### Error de archivos estáticos

**Síntomas:**
```
404 Not Found en /static/...
```

**Solución:**
1. Verifica que `collectstatic` se ejecutó:
   ```bash
   docker exec -it <container_id> ls -la /app/discord/staticfiles/
   ```
2. Si no existe, ejecuta:
   ```bash
   docker exec -it <container_id> python discord/manage.py collectstatic --noinput
   ```
3. Reinicia el contenedor

### Error de base de datos

**Síntomas:**
```
django.db.utils.OperationalError: connection refused
```

**Solución:**
1. Verifica variables de entorno de PostgreSQL
2. Verifica que la base de datos esté corriendo
3. Verifica conectividad desde el contenedor:
   ```bash
   docker exec -it <container_id> ping <POSTGRES_HOST>
   ```

### Error de pgvector

**Síntomas:**
```
django.db.utils.NotSupportedError: la extensión «vector» no está disponible
```

**Solución:**
1. Conecta a la base de datos
2. Ejecuta:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Verifica:
   ```sql
   SELECT * FROM pg_extension WHERE extname = 'vector';
   ```

### Ver logs

**En Dokploy:**
- Ve a tu aplicación → "Logs"
- Verás logs de todos los procesos (Nginx, Django, Bot)

**Desde terminal:**
```bash
# Logs del contenedor
docker logs -f <container_id>

# Logs de un proceso específico
docker exec -it <container_id> supervisorctl tail -f django
docker exec -it <container_id> supervisorctl tail -f discord_bot
```

---

## 📊 Monitoreo

### Verificar Estado de Procesos

```bash
docker exec -it <container_id> supervisorctl status
```

Deberías ver:
```
nginx                            RUNNING   pid 10, uptime 0:05:23
django                           RUNNING   pid 11, uptime 0:05:23
discord_bot                      RUNNING   pid 12, uptime 0:05:23
```

### Verificar Estado del Bot

```bash
# Ver logs del bot
docker logs <container_id> | grep "Bot listo"

# Verificar conexión a Discord
docker logs <container_id> | grep "discord"
```

### Verificar Estado de Django

```bash
# Verificar que responde
curl http://localhost:8000/admin/

# Ver logs de Django
docker logs <container_id> | grep "django"
```

---

## 🔄 Actualizaciones

### Actualizar Código

1. **Hacer push a tu repositorio:**
   ```bash
   git add .
   git commit -m "Actualización"
   git push origin main
   ```

2. **En Dokploy:**
   - Ve a tu aplicación
   - Haz clic en "Redeploy" o "Restart"
   - Dokploy reconstruirá la imagen automáticamente

### Actualizar Base de Datos

```bash
# Conectarte al contenedor
docker exec -it <container_id> bash

# Ejecutar migraciones
cd /app/discord
python manage.py migrate

# Re-indexar datos (si es necesario)
python manage.py index_training_data --clear
```

---

## 📝 Checklist de Despliegue

Antes de poner en producción:

- [ ] Dockerfile configurado correctamente
- [ ] Variables de entorno configuradas en Dokploy
- [ ] Base de datos PostgreSQL creada
- [ ] Extensión pgvector habilitada
- [ ] Migraciones ejecutadas
- [ ] Archivos estáticos recolectados
- [ ] Superusuario de Django creado
- [ ] Bot de Discord configurado
- [ ] Productos de Hotmart configurados (si aplica)
- [ ] Roles del chatbot configurados
- [ ] Datos de entrenamiento indexados
- [ ] Webhook de Hotmart configurado (si aplica)
- [ ] Logs monitoreados
- [ ] Backups configurados

---

**Última actualización**: Enero 2025  
**Versión**: 2.0.0

