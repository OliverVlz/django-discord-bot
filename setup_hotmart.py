import os
import sys
import django

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'discord')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'discord.discord.settings')
django.setup()

from invitation_roles.models import HotmartProduct

def setup_example_products():
    products = [
        {
            'product_id': '0',
            'product_name': 'Curso Básico IMAX',
            'discord_role_id': 'TU_ROLE_ID_BASICO',
            'is_subscription': True,
            'priority': 5,
            'is_active': True
        },
        {
            'product_id': '788921',
            'product_name': 'Curso Premium IMAX',
            'discord_role_id': 'TU_ROLE_ID_PREMIUM',
            'is_subscription': True,
            'priority': 10,
            'is_active': True
        },
    ]
    
    print("🔧 Configurando productos de ejemplo para Hotmart...")
    print("⚠️ IMPORTANTE: Debes editar los IDs de roles de Discord antes de usar en producción\n")
    
    for product_data in products:
        product, created = HotmartProduct.objects.get_or_create(
            product_id=product_data['product_id'],
            defaults=product_data
        )
        
        if created:
            print(f"✅ Producto creado: {product.product_name} (ID: {product.product_id})")
        else:
            print(f"ℹ️ Producto ya existe: {product.product_name} (ID: {product.product_id})")
    
    print("\n📝 Próximos pasos:")
    print("1. Edita los productos en el admin de Django (/admin/)")
    print("2. Reemplaza 'TU_ROLE_ID_BASICO' y 'TU_ROLE_ID_PREMIUM' con los IDs reales de Discord")
    print("3. Configura el webhook en Hotmart apuntando a: /invitation_roles/hotmart/webhook/")
    print("4. Reinicia el bot de Discord")

if __name__ == '__main__':
    setup_example_products()


