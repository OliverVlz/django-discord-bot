import os
import sys
import asyncio
from pathlib import Path

base_dir = Path(__file__).parent
discord_dir = base_dir / 'discord'

sys.path.insert(0, str(discord_dir))
sys.path.insert(0, str(base_dir))

os.chdir(str(discord_dir))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'discord.settings')

import django
django.setup()

from dotenv import load_dotenv
load_dotenv()

from chatbot_ai.vector_service import vector_service
from chatbot_ai.ai_service import ai_service

async def test_rag_query():
    print("=" * 70)
    print("🧪 Prueba de RAG - Sistema de Búsqueda Vectorial")
    print("=" * 70)
    print()
    
    pregunta = input("📝 Ingresa tu pregunta: ").strip()
    
    if not pregunta:
        print("❌ No ingresaste una pregunta")
        return
    
    print()
    print("🔍 Buscando contexto relevante en la base de conocimiento...")
    print()
    
    try:
        chunks = await vector_service.search_similar_chunks(pregunta, limit=5)
        
        if not chunks:
            print("⚠️  No se encontraron chunks relevantes en la base de datos.")
            print("   Esto puede significar que:")
            print("   - La base de datos de chunks está vacía")
            print("   - Necesitas ejecutar: python discord/manage.py index_training_data")
            return
        
        print(f"✅ Se encontraron {len(chunks)} chunks relevantes:")
        print()
        
        for i, chunk in enumerate(chunks, 1):
            print("-" * 70)
            print(f"📄 Chunk {i} (Similitud: {chunk['similarity']:.2%})")
            print(f"   Curso: {chunk['course']}")
            print(f"   Módulo: {chunk['module']}")
            print(f"   Archivo: {chunk['source_file']}")
            print()
            print(f"   Contenido:")
            contenido = chunk['content'][:500] + "..." if len(chunk['content']) > 500 else chunk['content']
            print(f"   {contenido}")
            print()
        
        print("=" * 70)
        print("📋 Contexto formateado para el LLM:")
        print("=" * 70)
        print()
        
        context_formatted = vector_service.format_context_for_llm(chunks)
        print(context_formatted)
        
        print()
        print("=" * 70)
        print("🤖 Simulando respuesta del sistema completo:")
        print("=" * 70)
        print()
        
        system_prompt = await ai_service.get_system_prompt(user_query=pregunta)
        
        print("📝 System Prompt (primeros 500 caracteres):")
        print(system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt)
        print()
        
        print("💡 El LLM recibirá:")
        print("   1. El system prompt con el contexto RAG")
        print("   2. El historial de conversación (si existe)")
        print("   3. Tu pregunta")
        print()
        print("✅ El sistema está listo para generar una respuesta basada en este contexto")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_rag_query())

