from http.server import BaseHTTPRequestHandler
import json
import os
import requests
from requests.adapters import HTTPAdapter, Retry

URL_SUPABASE = os.environ.get("SUPABASE_URL", "")
KEY_SUPABASE = os.environ.get("SUPABASE_SECRET_KEY", "")
FRONTEND_DOMAIN = os.environ.get("FRONTEND_DOMAIN", "https://sistema-de-facturacion-bot-ws.vercel.app")

# Sesión con reintentos automáticos para fallos transitorios de red
# (timeouts cortos, 502/503/504 puntuales, etc.)
session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[502, 503, 504],
    allowed_methods=["POST"],
)
session.mount("https://", HTTPAdapter(max_retries=retries))


def validar_factura(data):
    """Valida los datos mínimos antes de tocar la base de datos.
    Devuelve un mensaje de error (str) o None si todo está bien."""
    if not data.get("id_factura"):
        return "Falta id_factura"
    if not data.get("nombre"):
        return "Falta el nombre del cliente"

    productos = data.get("productos", [])
    if not productos:
        return "La factura no tiene productos"

    for i, p in enumerate(productos):
        nombre = p.get("nombre") or p.get("nombre_producto")
        cantidad = p.get("cantidad")
        precio_unitario = p.get("precioUnitario") if p.get("precioUnitario") is not None else p.get("precio_unitario")
        precio_total = p.get("precioTotal") if p.get("precioTotal") is not None else p.get("precio_total")

        if not nombre:
            return f"Producto #{i+1}: falta el nombre"
        if cantidad is None or float(cantidad) <= 0:
            return f"Producto #{i+1} ({nombre}): cantidad inválida"
        if precio_unitario is None or float(precio_unitario) < 0:
            return f"Producto #{i+1} ({nombre}): precio unitario inválido"
        if precio_total is None or float(precio_total) < 0:
            return f"Producto #{i+1} ({nombre}): precio total inválido"

    for campo in ("subtotal_usd", "total_usd", "subtotal_bs", "total_bs"):
        if data.get(campo) is None:
            return f"Falta el campo {campo}"

    return None


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def _responder(self, status_code, payload):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            factura_data = json.loads(post_data.decode('utf-8'))
        except (json.JSONDecodeError, ValueError):
            self._responder(400, {"status": "error", "message": "JSON inválido en la solicitud"})
            return

        # === 1. Validación previa (evita insertos parciales por datos malos) ===
        error_validacion = validar_factura(factura_data)
        if error_validacion:
            self._responder(400, {"status": "error", "message": error_validacion})
            return

        # === 2. Guardado ATÓMICO vía RPC: cabecera + detalles en una sola transacción ===
        p_factura = {
            "id_factura": factura_data.get("id_factura"),
            "nombre": factura_data.get("nombre"),
            "apellido": factura_data.get("apellido", ""),
            "cedula": factura_data.get("cedula", ""),
            "telefono": factura_data.get("telefono"),
            "vendedor": factura_data.get("vendedor", "Cajero General"),
            "subtotal_usd": factura_data.get("subtotal_usd"),
            "descuento_usd": factura_data.get("descuento_usd", 0),
            "total_usd": factura_data.get("total_usd"),
            "subtotal_bs": factura_data.get("subtotal_bs"),
            "descuento_bs": factura_data.get("descuento_bs", 0),
            "total_bs": factura_data.get("total_bs"),
            "metodo_pago": factura_data.get("metodo_pago"),
            "referencia": factura_data.get("referencia"),
            "banco": factura_data.get("banco"),
        }

        p_detalles = [
            {
                "nombre_producto": p.get("nombre") or p.get("nombre_producto"),
                "cantidad": p.get("cantidad"),
                "precio_unitario": p.get("precioUnitario") if p.get("precioUnitario") is not None else p.get("precio_unitario"),
                "precio_total": p.get("precioTotal") if p.get("precioTotal") is not None else p.get("precio_total"),
            }
            for p in factura_data.get("productos", [])
        ]

        headers_supabase = {
            "apikey": KEY_SUPABASE,
            "Authorization": f"Bearer {KEY_SUPABASE}",
            "Content-Type": "application/json",
        }

        url_rpc = f"{URL_SUPABASE}/rest/v1/rpc/guardar_factura_completa"

        try:
            res = session.post(
                url_rpc,
                json={"p_factura": p_factura, "p_detalles": p_detalles},
                headers=headers_supabase,
                timeout=15,
            )
        except requests.exceptions.RequestException as e:
            self._responder(502, {"status": "error", "message": f"No se pudo conectar con la base de datos: {e}"})
            return

        if res.status_code not in (200, 204):
            # La transacción se revirtió por completo en Postgres: nada quedó guardado a medias.
            print(f"⚠️ Falló guardar_factura_completa: {res.status_code} {res.text}")
            self._responder(502, {
                "status": "error",
                "message": f"No se pudo guardar la factura: {res.text}",
            })
            return

        # === 3. Envío al puente de WhatsApp (solo si el guardado fue exitoso) ===
        URL_PUENTE = os.environ.get("URL_PUENTE", "")
        telefono_cliente = factura_data.get("telefono")
        nombre_cliente = factura_data.get("nombre", "Cliente")
        id_factura = factura_data.get("id_factura")

        if URL_PUENTE and telefono_cliente and telefono_cliente != "N/A":
            link_factura = f"{FRONTEND_DOMAIN}/factura.html?id={id_factura}"
            payload_puente = {
                "to": telefono_cliente,
                "message": f"👋 ¡Hola, *{nombre_cliente}*!\n\nAquí tienes el link de tu factura digital:\n🔗 {link_factura}\n\n¡Gracias por tu compra! ✨"
            }
            try:
                url_endpoint_puente = f"{URL_PUENTE.rstrip('/')}/send-message"
                requests.post(url_endpoint_puente, json=payload_puente, timeout=4)
            except Exception as ws_err:
                # Esto es informativo, no crítico: la factura ya está guardada correctamente.
                print(f"⚠️ Alerta: El puente no procesó el mensaje de WhatsApp: {ws_err}")

        # === 4. Respuesta exitosa real (la factura y sus productos SÍ están guardados) ===
        self._responder(200, {"status": "success", "message": "Factura y productos guardados correctamente"})
