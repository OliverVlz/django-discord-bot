import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

async def test_openai_api():
    api_key = os.environ.get('OPENAI_API_KEY', '')
    
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY no está configurada en .env")
        return False
    
    print(f"✅ API Key encontrada: {api_key[:10]}...{api_key[-4:]}")
    print("🔄 Probando conexión con OpenAI API...\n")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": "Responde solo con 'OK' si recibes este mensaje."}
        ],
        "max_tokens": 10,
        "temperature": 0.7
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    tokens = result['usage']['total_tokens']
                    
                    print("✅ ¡API de OpenAI funciona correctamente!")
                    print(f"📝 Respuesta: {content}")
                    print(f"🎯 Tokens usados: {tokens}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ ERROR: OpenAI API respondió con código {response.status}")
                    print(f"📄 Detalles: {error_text}")
                    return False
                    
    except asyncio.TimeoutError:
        print("❌ ERROR: Timeout al conectar con OpenAI API")
        return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🧪 Prueba de API de OpenAI")
    print("=" * 50)
    print()
    
    success = asyncio.run(test_openai_api())
    
    print()
    print("=" * 50)
    if success:
        print("✅ Prueba completada exitosamente")
    else:
        print("❌ Prueba falló")
    print("=" * 50)
