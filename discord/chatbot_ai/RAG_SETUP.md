# Configuración RAG con pgvector

## Requisitos

1. **PostgreSQL con extensión pgvector**
2. **API Key de OpenAI** en `.env` (para embeddings y chat)

## Variables de entorno requeridas (.env)

```env
# Base de datos
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DATABASE=django_discord_bot

# API Key (OBLIGATORIA - solo desde .env)
OPENAI_API_KEY=sk-...
```

**Nota**: Las API keys SOLO se leen desde `.env`, no desde Django Admin.

## Opción 1: Usar Docker (Recomendado)

### 1. Iniciar Docker Desktop

### 2. Ejecutar el contenedor de PostgreSQL con pgvector

```bash
cd C:\Work\Discord\django-discord-bot
docker-compose up -d
```

### 3. Actualizar variables de entorno

Agregar/modificar en tu archivo `.env`:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DATABASE=django_discord_bot
```

### 4. Ejecutar migraciones

```bash
cd discord
..\venv\Scripts\python manage.py migrate
```

### 5. Indexar datos de entrenamiento

```bash
# Ver qué se indexará (dry-run)
..\venv\Scripts\python manage.py index_training_data --dry-run

# Indexar los archivos
..\venv\Scripts\python manage.py index_training_data --clear
```

## Opción 2: Usar Neon (PostgreSQL en la nube - Gratis)

### 1. Crear cuenta en [Neon](https://neon.tech)

### 2. Crear un proyecto nuevo

- Neon ya tiene pgvector habilitado por defecto

### 3. Copiar la connection string y actualizar `.env`

```env
POSTGRES_HOST=tu-proyecto.neon.tech
POSTGRES_PORT=5432
POSTGRES_USER=tu-usuario
POSTGRES_PASSWORD=tu-password
POSTGRES_DATABASE=neondb
```

### 4. Habilitar pgvector en Neon

Ejecutar en la consola SQL de Neon:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 5. Ejecutar migraciones e indexar

```bash
cd discord
..\venv\Scripts\python manage.py migrate
..\venv\Scripts\python manage.py index_training_data --clear
```

## Comandos útiles

### Ver estadísticas de indexación

```bash
..\venv\Scripts\python manage.py index_training_data --dry-run
```

### Re-indexar todos los archivos

```bash
..\venv\Scripts\python manage.py index_training_data --clear
```

## Cómo funciona

1. Los archivos de `ai-training/` se dividen en chunks de ~500 tokens
2. Cada chunk se convierte en un vector de 1536 dimensiones usando OpenAI embeddings
3. Los vectores se almacenan en PostgreSQL con pgvector
4. Cuando un usuario hace una pregunta:
   - Se crea un embedding de la pregunta
   - Se buscan los 5 chunks más similares
   - Solo esos chunks se envían al LLM como contexto

## Costos estimados

- **Indexación inicial**: ~$0.01 (una sola vez)
- **Por consulta**: ~$0.0001 (prácticamente gratis)
