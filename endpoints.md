¿Cómo recibirá la solicitud el suscriptor?

El suscriptor recibirá un email con un link, válido por tres días, para aceptar o no la reactivación de la suscripción en cuestión.

Parámetros de la solicitud
Path
subscriber_code
obligatorio

Código exclusivo de suscriptor cuya suscripción deseas reactivar.

Body
charge

Indica si debe realizar un nueva cobro paral os compradores al reactivar las suscripciones. Este genera un nuevo cobro si marcas como true, por estándar tu valor es false. La fecha de cobro continuará la misma de antes de la suscripción haber sido desactivada.

`curl --location --request POST 'https://developers.hotmart.com/payments/api/v1/subscriptions/:subscriber_code/reactivate' \
  --header 'Authorization: Bearer :access_token' \
  --header 'Content-Type: application/json' \
  --data-raw '{
      "charge": :charge
  }'`
