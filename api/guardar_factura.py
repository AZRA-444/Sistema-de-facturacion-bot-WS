from http.server import BaseHTTPRequestHandler
import json
import os
import requests

URL_SUPABASE = os.environ.get("SUPABASE_URL", "")
KEY_SUPABASE = os.environ.get("SUPABASE_SECRET_KEY", "")
URL_PUENTE = os.environ.get("URL_PUENTE_WHATSAPP", "")
FRONTEND_DOMAIN = os.environ.get("FRONTEND_DOMAIN", "https://sistema-de-facturacion-bot-ws.vercel.app")

class handler(BaseHTTPRequestHandler):

    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self):
        try:
            # Leer body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            factura_data = json.loads(post_data.decode('utf-8'))

            # ====================== VALIDACIÓN ======================
            required_fields = ["id_factura", "nombre", "telefono", "productos"]
            for field in required_fields:
                if not factura_data.get(field):
                    raise ValueError(f"Campo requerido faltante: {field}")

            if not isinstance(factura_data.get("productos"), list) or len(factura_data["productos"]) == 0:
                raise ValueError("La factura debe contener al menos un producto")

            # ====================== PREPARAR PAYLOAD FACTURA ======================
            headers_supabase = {
                "apikey": KEY_SUPABASE,
                "Authorization": f"Bearer {KEY_SUPABASE}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }

            factura_payload = {
                "id_factura": factura_data["id_factura"],
                "nombre": factura_data["nombre"],
                "apellido": factura_data.get("apellido", ""),
                "cedula": factura_data.get("cedula", ""),
                "telefono": factura_data["telefono"],
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

            # ====================== INSERTAR FACTURA ======================
            res_factura = requests.post(
                f"{URL_SUPABASE}/rest/v1/facturas",
                json=factura_payload,
                headers=headers_supabase,
                timeout=10
            )

            if res_factura.status_code not in (200, 201):
                raise Exception(f"Error Supabase Factura: {res_factura.status_code} - {res_factura.text[:200]}")

            # ====================== INSERTAR DETALLES ======================
            detalles = []
            for p in factura_data["productos"]:
                detalles.append({
                    "id_factura": factura_data["id_factura"],
                    "nombre_producto": p.get("nombre") or p.get("nombre_producto"),
                    "cantidad": p["cantidad"],
                    "precio_unitario": p["precioUnitario"],
                    "precio_total": p["precioTotal"]
                })

            if detalles:
                res_detalles = requests.post(
                    f"{URL_SUPABASE}/rest/v1/factura_detalles",
                    json=detalles,
                    headers=headers_supabase,
                    timeout=10
                )
                if res_detalles.status_code not in (200, 201):
                    print(f"⚠️ Error en detalles: {res_detalles.text}")

            # ====================== LINK Y WHATSAPP ======================
            link_factura = f"{FRONTEND_DOMAIN}/factura.html?id={factura_data['id_factura']}"

            if URL_PUENTE and factura_data.get("telefono") and factura_data["telefono"] != "N/A":
                mensaje = (
                    f"👋 Hola {factura_data['nombre']}\n\n"
                    f"🧾 Tu factura *{factura_data['id_factura']}* está lista:\n"
                    f"{link_factura}\n\n"
                    f"💰 Total: ${factura_data.get('total_usd', 0)} USD\n"
                    f"Gracias por tu compra"
                )
                try:
                    requests.post(
                        f"{URL_PUENTE}/send-message",
                        json={"to": factura_data["telefono"], "message": mensaje},
                        timeout=8
                    )
                except Exception as e:
                    print("WhatsApp error:", e)

            # ====================== RESPUESTA EXITOSA ======================
            self.send_response(200)
            self._send_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            self.wfile.write(json.dumps({
                "status": "success",
                "id_factura": factura_data["id_factura"],
                "link": link_factura,
                "message": "Factura procesada correctamente"
            }).encode('utf-8'))

        except json.JSONDecodeError:
            self._error_response("JSON inválido en la petición")
        except ValueError as ve:
            self._error_response(str(ve))
        except Exception as e:
            print("Error backend:", str(e))  # Para logs en Vercel
            self._error_response(str(e))

    def _error_response(self, message):
        self.send_response(400)
        self._send_cors_headers()
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "error",
            "message": message
        }).encode('utf-8'))



