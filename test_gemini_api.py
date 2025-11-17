import os
import sys
import asyncio
import aiohttp
import django

base_dir = os.path.dirname(__file__)
sys.path.insert(0, base_dir)
sys.path.insert(0, os.path.join(base_dir, 'discord'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'discord.discord.settings')

sync_to_async = None
BotConfiguration = None
DJANGO_AVAILABLE = False

try:
    django.setup()
    from asgiref.sync import sync_to_async
    from invitation_roles.models import BotConfiguration
    DJANGO_AVAILABLE = True
except Exception as e:
    print(f"[!] No se pudo cargar Django: {e}")
    print("[!] Solo se buscara en variables de entorno\n")

async def test_gemini_api():
    print("Probando API de Gemini...\n")
    
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key and DJANGO_AVAILABLE:
        if sync_to_async is not None and BotConfiguration is not None:
            print("[!] No se encontro GEMINI_API_KEY en variables de entorno")
            print("[?] Buscando en base de datos...")
            try:
                config_model = BotConfiguration
                async_func = sync_to_async
                config = await async_func(
                    lambda: config_model.objects.filter(name='gemini_api_key', is_active=True).first()
                )()
                if config:
                    api_key = config.value
                    print(f"[OK] API Key encontrada en BD: {api_key[:10]}...")
            except Exception as e:
                print(f"[!] Error buscando en BD: {e}")
    
    if not api_key:
        print("[!] No se encontro GEMINI_API_KEY")
        print("[?] Configura la variable de entorno:")
        print("    PowerShell: $env:GEMINI_API_KEY='tu-api-key'")
        print("    CMD: set GEMINI_API_KEY=tu-api-key")
        print("\n[X] No se puede continuar sin API key")
        return
    else:
        if not api_key.startswith('AI'):
            print(f"[OK] API Key encontrada: {api_key[:10]}...")
        else:
            print(f"[OK] API Key encontrada: {api_key[:10]}...")
    
    model_name = "gemini-pro"
    api_version = "v1beta"
    
    print("[?] Listando modelos disponibles...")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    for api_version in ["v1beta", "v1"]:
        list_url = f"https://generativelanguage.googleapis.com/{api_version}/models?key={api_key}"
        print(f"\nBuscando modelos en API {api_version}...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    list_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if 'models' in result:
                            print(f"[OK] Modelos disponibles en {api_version}:")
                            modelos_disponibles = []
                            for model in result['models']:
                                model_name = model.get('name', '').replace('models/', '')
                                supported_methods = model.get('supportedGenerationMethods', [])
                                if 'generateContent' in supported_methods:
                                    print(f"   - {model_name}")
                                    modelos_disponibles.append((model_name, api_version))
                            
                            if modelos_disponibles:
                                print(f"\n[OK] Probando modelos que soportan generateContent...")
                                data = {
                                    "contents": [{
                                        "parts": [{"text": "Hola"}],
                                        "role": "user"
                                    }],
                                    "generationConfig": {
                                        "temperature": 0.7,
                                        "maxOutputTokens": 10
                                    }
                                }
                                
                                for model_name, api_ver in modelos_disponibles[:3]:
                                    print(f"\nProbando: {model_name} (API: {api_ver})")
                                    url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{model_name}:generateContent?key={api_key}"
                                    
                                    try:
                                        async with aiohttp.ClientSession() as test_session:
                                            async with test_session.post(
                                                url,
                                                headers=headers,
                                                json=data,
                                                timeout=aiohttp.ClientTimeout(total=10)
                                            ) as test_response:
                                                if test_response.status == 200:
                                                    test_result = await test_response.json()
                                                    content = test_result['candidates'][0]['content']['parts'][0]['text']
                                                    print(f"[OK] EXITO! Modelo {model_name} funciona")
                                                    print(f"Respuesta de prueba: {content}")
                                                    print(f"\n[OK] Configuracion recomendada:")
                                                    print(f"   Modelo: {model_name}")
                                                    print(f"   Version API: {api_ver}\n")
                                                    return
                                                else:
                                                    print(f"[X] Error {test_response.status}")
                                    except Exception as e:
                                        print(f"[X] Error: {str(e)[:50]}")
                        else:
                            print(f"[X] No se encontraron modelos en la respuesta")
                    else:
                        error_text = await response.text()
                        print(f"[X] Error {response.status}: {error_text[:100]}")
        except Exception as e:
            print(f"[X] Error listando modelos: {str(e)[:100]}")
    
    print("\n[X] No se pudieron encontrar modelos disponibles.")
    return

if __name__ == "__main__":
    asyncio.run(test_gemini_api())
