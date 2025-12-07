# 📋 Payloads Reales para Pruebas - Hotmart Webhooks

Basándome en los datos reales de `hotmart.md` y tu estructura de prueba, aquí tienes los payloads completos y realistas para probar todos los eventos de Hotmart que maneja tu sistema.

## 🎯 Campos Clave para Tu Sistema

**Para que funcionen correctamente, asegúrate de que:**

1. **Product ID**: `788921` (debe estar configurado en `HotmartProduct`)
2. **Subscriber Code**: `SUB001` (identificador único de suscripción)
3. **Email**: `olierel12@gmail.com` (usuario de prueba)
4. **Transaction ID**: `HP12345670000TEST` (único para cada evento)
5. **Event ID**: Único para cada webhook (cambiar por cada prueba)

## ⚠️ Notas Importantes

- **Fechas**: Usa timestamps en milisegundos (como en los ejemplos reales)
- **IDs únicos**: Cambia los IDs para evitar conflictos en pruebas
- **Product ID**: Debe existir en tu base de datos configurado
- **Versión**: Siempre `"2.0.0"` (versión actual de Hotmart)

---

## 1. **PURCHASE_APPROVED** (Suscripción Nueva)

```json
{
  "event": "PURCHASE_APPROVED",
  "id": "1f1ab22e-ae66-4f58-a76c-8f0e4d0db59b",
  "creation_date": 1759194927364,
  "version": "2.0.0",
  "data": {
    "product": {
      "id": 788921,
      "name": "Curso Premium IMAX",
      "support_email": "support@hotmart.com.br",
      "has_co_production": false,
      "warranty_date": "2024-12-27T00:00:00Z",
      "is_physical_product": false,
      "ucode": "fb056612-bcc6-4217-9e6d-2a5d1110ac2f"
    },
    "purchase": {
      "transaction": "HP12345670000TEST",
      "status": "APPROVED",
      "approved_date": 1759194927000,
      "order_date": 1759194926000,
      "price": {
        "value": 100.0,
        "currency_value": "USD"
      },
      "original_offer_price": {
        "value": 150.0,
        "currency_value": "USD"
      },
      "full_price": {
        "value": 100.0,
        "currency_value": "USD"
      },
      "payment": {
        "type": "CREDIT_CARD",
        "installments_number": 1
      },
      "buyer_ip": "192.168.1.1",
      "checkout_country": {
        "iso": "US",
        "name": "United States"
      },
      "business_model": "I",
      "is_funnel": false,
      "offer": {
        "code": "PREMIUM2024"
      }
    },
    "buyer": {
      "email": "olierel12@gmail.com",
      "name": "Usuario de Prueba",
      "first_name": "Usuario",
      "last_name": "de Prueba",
      "document": "12345678901",
      "document_type": "CPF",
      "checkout_phone": "5551234567",
      "checkout_phone_code": "555",
      "address": {
        "zipcode": "12345",
        "country": "United States",
        "country_iso": "US",
        "state": "California",
        "city": "Los Angeles",
        "neighborhood": "Downtown",
        "address": "123 Main St",
        "number": "123",
        "complement": "Apt 4B"
      }
    },
    "subscription": {
      "subscriber": {
        "code": "SUB001"
      },
      "plan": {
        "id": 1,
        "name": "Plan Mensual"
      },
      "status": "ACTIVE"
    },
    "producer": {
      "name": "Producer Name",
      "legal_nature": "Pessoa Física",
      "document": "12345678965"
    },
    "commissions": [
      {
        "source": "PRODUCER",
        "value": 85.0,
        "currency_value": "USD"
      }
    ]
  }
}
```

**Acción esperada:**

- ✅ Crea nueva suscripción con estado `ACTIVE`
- ✅ Genera invitación de Discord
- ✅ Envía email al usuario

---

## 2. **SUBSCRIPTION_CANCELLATION**

```json
{
  "event": "SUBSCRIPTION_CANCELLATION",
  "id": "a75428a4-7d61-4405-b86b-ecc5a84f9792",
  "creation_date": 1759194927318,
  "version": "2.0.0",
  "data": {
    "subscriber": {
      "code": "SUB001",
      "name": "Usuario de Prueba",
      "email": "olierel12@gmail.com",
      "phone": {
        "dddCell": "",
        "phone": "",
        "dddPhone": "",
        "cell": ""
      }
    },
    "subscription": {
      "id": 4148584,
      "plan": {
        "name": "Plan Mensual",
        "id": 1
      },
      "status": "CANCELLED"
    },
    "product": {
      "id": 788921,
      "name": "Curso Premium IMAX"
    },
    "date_next_charge": 1761876927000,
    "actual_recurrence_value": 100.0,
    "cancellation_date": 1759194927000
  }
}
```

**Acción esperada:**

- ✅ Cancela suscripción (estado `CANCELLED`)
- ✅ Revoca roles de Discord
- ✅ Aplica rol visitante si está configurado

---

## 3. **UPDATE_SUBSCRIPTION_CHARGE_DATE**

```json
{
  "event": "UPDATE_SUBSCRIPTION_CHARGE_DATE",
  "id": "e3e23f82-04a3-4a53-a633-4cf8ab029e07",
  "creation_date": 1759194927490,
  "version": "2.0.0",
  "hottok": "A2m1cr29DuAQmNhg1Z6lftUV5Hh8kH5addb703-70a2-4699-803c-04da58b9579a",
  "data": {
    "subscriber": {
      "code": "SUB001",
      "name": "Usuario de Prueba",
      "email": "olierel12@gmail.com"
    },
    "subscription": {
      "product": {
        "id": 788921,
        "name": "Curso Premium IMAX"
      },
      "old_charge_day": 15,
      "date_next_charge": "2024-02-15T12:00:00.000Z",
      "new_charge_day": 20,
      "status": "ACTIVE"
    },
    "plan": {
      "offer": {
        "code": "PREMIUM2024"
      },
      "name": "Plan Mensual",
      "id": 1
    }
  }
}
```

**Acción esperada:**

- ✅ Actualiza fecha de próximo cobro
- ✅ Solo registro informativo (no afecta roles)

---

## 4. **PURCHASE_COMPLETE**

```json
{
  "event": "PURCHASE_COMPLETE",
  "id": "d1e959b9-0ef3-4cfd-9928-71c3dcb95c5c",
  "creation_date": 1759194927250,
  "version": "2.0.0",
  "data": {
    "product": {
      "id": 788921,
      "name": "Curso Premium IMAX",
      "support_email": "support@hotmart.com.br",
      "has_co_production": false,
      "warranty_date": "2024-12-27T00:00:00Z",
      "is_physical_product": false,
      "ucode": "fb056612-bcc6-4217-9e6d-2a5d1110ac2f"
    },
    "purchase": {
      "transaction": "HP12345670000TEST",
      "status": "COMPLETED",
      "approved_date": 1759194927000,
      "order_date": 1759194926000,
      "price": {
        "value": 100.0,
        "currency_value": "USD"
      },
      "payment": {
        "type": "CREDIT_CARD",
        "installments_number": 1
      },
      "business_model": "I"
    },
    "buyer": {
      "email": "olierel12@gmail.com",
      "name": "Usuario de Prueba",
      "first_name": "Usuario",
      "last_name": "de Prueba"
    },
    "subscription": {
      "subscriber": {
        "code": "SUB001"
      },
      "plan": {
        "id": 1,
        "name": "Plan Mensual"
      },
      "status": "ACTIVE"
    },
    "producer": {
      "name": "Producer Name",
      "legal_nature": "Pessoa Física",
      "document": "12345678965"
    }
  }
}
```

**Acción esperada:**

- ✅ Solo registro de transacción completada
- ✅ No afecta suscripciones ni roles

---

## 5. **PURCHASE_PROTEST**

```json
{
  "event": "PURCHASE_PROTEST",
  "id": "18e79aba-ca64-42d6-911e-50ff07c57e23",
  "creation_date": 1759195726356,
  "version": "2.0.0",
  "data": {
    "product": {
      "id": 788921,
      "name": "Curso Premium IMAX",
      "support_email": "support@hotmart.com.br",
      "has_co_production": false,
      "warranty_date": "2024-12-27T00:00:00Z",
      "is_physical_product": false,
      "ucode": "fb056612-bcc6-4217-9e6d-2a5d1110ac2f"
    },
    "purchase": {
      "transaction": "HP12345670000TEST",
      "status": "DISPUTE",
      "approved_date": 1759194927000,
      "order_date": 1759194926000,
      "price": {
        "value": 100.0,
        "currency_value": "USD"
      },
      "payment": {
        "type": "CREDIT_CARD",
        "installments_number": 1
      },
      "business_model": "I"
    },
    "buyer": {
      "email": "olierel12@gmail.com",
      "name": "Usuario de Prueba",
      "first_name": "Usuario",
      "last_name": "de Prueba"
    },
    "subscription": {
      "subscriber": {
        "code": "SUB001"
      },
      "plan": {
        "id": 1,
        "name": "Plan Mensual"
      },
      "status": "ACTIVE"
    },
    "producer": {
      "name": "Producer Name",
      "legal_nature": "Pessoa Física",
      "document": "12345678965"
    }
  }
}
```

**Acción esperada:**

- ✅ Suspende suscripción (estado `SUSPENDED`)
- ✅ NO revoca roles (mantiene acceso durante investigación)

---

## 6. **PURCHASE_REFUNDED**

```json
{
  "event": "PURCHASE_REFUNDED",
  "id": "d7321ad2-82e4-43e3-a9a8-d2fc05b6a02e",
  "creation_date": 1759195726425,
  "version": "2.0.0",
  "data": {
    "product": {
      "id": 788921,
      "name": "Curso Premium IMAX",
      "support_email": "support@hotmart.com.br",
      "has_co_production": false,
      "warranty_date": "2024-12-27T00:00:00Z",
      "is_physical_product": false,
      "ucode": "fb056612-bcc6-4217-9e6d-2a5d1110ac2f"
    },
    "purchase": {
      "transaction": "HP12345670000TEST",
      "status": "REFUNDED",
      "approved_date": 1759194927000,
      "order_date": 1759194926000,
      "price": {
        "value": 100.0,
        "currency_value": "USD"
      },
      "payment": {
        "type": "CREDIT_CARD",
        "installments_number": 1
      },
      "business_model": "I"
    },
    "buyer": {
      "email": "olierel12@gmail.com",
      "name": "Usuario de Prueba",
      "first_name": "Usuario",
      "last_name": "de Prueba"
    },
    "subscription": {
      "subscriber": {
        "code": "SUB001"
      },
      "plan": {
        "id": 1,
        "name": "Plan Mensual"
      },
      "status": "ACTIVE"
    },
    "producer": {
      "name": "Producer Name",
      "legal_nature": "Pessoa Física",
      "document": "12345678965"
    }
  }
}
```

**Acción esperada:**

- ✅ Cancela suscripción (estado `CANCELLED`)
- ✅ Revoca roles de Discord
- ✅ Aplica rol visitante si está configurado

---

## 7. **SWITCH_PLAN**

```json
{
  "event": "SWITCH_PLAN",
  "id": "be776db7-77c1-4b3f-a14f-79d59a38f4c6",
  "creation_date": 1759194927441,
  "version": "2.0.0",
  "data": {
    "plans": [
      {
        "offer": {
          "key": "n6hup357"
        },
        "current": true,
        "name": "Plan Anual Premium",
        "id": 2
      },
      {
        "offer": {
          "key": "n6hup355"
        },
        "current": false,
        "name": "Plan Mensual",
        "id": 1
      }
    ],
    "switch_plan_date": 1759194927441,
    "subscription": {
      "subscriber_code": "SUB001",
      "product": {
        "id": 788921,
        "name": "Curso Premium IMAX"
      },
      "user": {
        "email": "olierel12@gmail.com"
      },
      "status": "ACTIVE"
    }
  }
}
```

**Acción esperada:**

- ✅ Actualiza producto/plan de la suscripción
- ✅ Detecta upgrade/downgrade según prioridad
- ✅ Asigna nuevo rol o envía invitación

---

## 🔧 Cómo Usar Estos Payloads

### 1. **Configuración Previa**

```python
# Asegúrate de tener configurado en BotConfiguration:
HotmartProduct.objects.create(
    product_id='788921',
    product_name='Curso Premium IMAX',
    discord_role_id='123456789012345678',  # ID del rol en Discord
    is_subscription=True,
    is_active=True,
    priority=10
)
```

### 2. **Pruebas con cURL**

```bash
# Ejemplo para PURCHASE_APPROVED
curl -X POST http://localhost:8000/invitation_roles/hotmart/webhook/ \
  -H "Content-Type: application/json" \
  -d @purchase_approved.json
```

### 3. **Verificación de Resultados**

- Revisa la tabla `HotmartSubscription` para ver si se creó/actualizó
- Revisa la tabla `HotmartTransaction` para ver el registro
- Verifica los logs del sistema para confirmar acciones

### 4. **IDs Únicos por Prueba**

Cambia estos campos en cada prueba:

- `id` (event ID)
- `transaction` (transaction ID)
- `creation_date` (timestamp)

---

## 📊 Flujo de Pruebas Recomendado

1. **PURCHASE_APPROVED** → Crea suscripción
2. **PURCHASE_COMPLETE** → Confirma compra
3. **UPDATE_SUBSCRIPTION_CHARGE_DATE** → Actualiza fecha
4. **SWITCH_PLAN** → Cambia plan
5. **SUBSCRIPTION_CANCELLATION** → Cancela suscripción
6. **PURCHASE_APPROVED** (mismo subscriber_code) → Reactiva suscripción

Estos payloads están basados en la estructura real de Hotmart y deberían funcionar perfectamente con tu sistema. Puedes usarlos para probar cada escenario de evento que maneja tu integración.




