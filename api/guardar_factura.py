from http.server import BaseHTTPRequestHandler
import json
import os
import requests
from urllib.parse import urlparse

URL_SUPABASE = os.environ.get("SUPABASE_URL", "")
KEY_SUPABASE = os.environ.get("SUPABASE_SECRET_KEY", "")
URL_PUENTE = os.environ.get("URL_PUENTE_WHATSAPP", "")
FRONTEND_DOMAIN = os.environ.get("FRONTEND_DOMAIN", "https://tu-proyecto.vercel.app")

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self._send_cors_headers()
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            factura_data = json.loads(post_data.decode('utf-8'))

            # ====================== VALIDACIÓN SEGURA ======================
            required_fields = ["id_factura", "nombre", "telefono", "productos"]
            for field in required_fields:
                if not factura_data.get(field):
                    raise ValueError(f"Campo requerido faltante: {field}")

            if not isinstance(factura_data.get("productos"), list) or len(factura_data["productos"]) == 0:
                raise ValueError("La factura debe contener al menos un producto")

            # ====================== INSERTAR FACTURA ======================
            headers = {
                "apikey": KEY_SUPABASE,
                "Authorization": f"Bearer {KEY_SUPABASE}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }

            factura_payload = {
                "id_factura": factura_data["id_factura"],
                "nombre": factura_data["nombre"],
                "apellido": factura_data.get("apellido"),
                "cedula": factura_data.get("cedula"),
                "telefono": factura_data["telefono"],
                "vendedor": factura_data.get("vendedor"),
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

            res_factura = requests.post(
                f"{URL_SUPABASE}/rest/v1/facturas",
                json=factura_payload,
                headers=headers
            )

            if res_factura.status_code not in (200, 201):
                raise Exception(f"Error al guardar factura: {res_factura.text}")

            # ====================== INSERTAR DETALLES ======================
            detalles = []
            for p in factura_data["productos"]:
                detalles.append({
                    "id_factura": factura_data["id_factura"],
                    "nombre_producto": p["nombre"],
                    "cantidad": p["cantidad"],
                    "precio_unitario": p["precioUnitario"],
                    "precio_total": p["precioTotal"]
                })

            if detalles:
                res_detalles = requests.post(
                    f"{URL_SUPABASE}/rest/v1/factura_detalles",
                    json=detalles,
                    headers=headers
                )
                if res_detalles.status_code not in (200, 201):
                    print("⚠️ Error guardando detalles:", res_detalles.text)

            # ====================== LINK PÚBLICO ======================
            link_factura = f"{FRONTEND_DOMAIN}/factura.html?id={factura_data['id_factura']}"

            # ====================== WHATSAPP ======================
            if URL_PUENTE and factura_data.get("telefono") and factura_data["telefono"] != "N/A":
                mensaje = (
                    f"👋 Hola *{factura_data['nombre']}*\n\n"
                    f"🧾 Tu factura *{factura_data['id_factura']}* está lista:\n"
                    f"{link_factura}\n\n"
                    f"💰 Total: ${factura_data.get('total_usd', 0)} USD\n"
                    f"Gracias por tu compra ✨"
                )

                try:
                    requests.post(
                        f"{URL_PUENTE}/send-message",
                        json={"to": factura_data["telefono"], "message": mensaje},
                        timeout=8
                    )
                except Exception as e:
                    print("WhatsApp error:", e)

            # ====================== RESPUESTA ======================
            self._send_cors_headers()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            self.wfile.write(json.dumps({
                "status": "success",
                "id_factura": factura_data["id_factura"],
                "link": link_factura,
                "message": "Factura procesada correctamente"
            }).encode('utf-8'))

        except Exception as e:
            self._send_cors_headers()
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "error",
                "message": str(e)
            }).encode('utf-8'))

    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
