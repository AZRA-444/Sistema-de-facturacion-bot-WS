from http.server import BaseHTTPRequestHandler
import json
import os
import requests

URL_SUPABASE = os.environ.get("SUPABASE_URL", "")
KEY_SUPABASE = os.environ.get("SUPABASE_SECRET_KEY", "")
URL_PUENTE = os.environ.get("URL_PUENTE_WHATSAPP", "")

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            factura_data = json.loads(post_data.decode('utf-8'))

            # =========================
            # 1. VALIDACIÓN BÁSICA
            # =========================
            if not factura_data.get("telefono") or not factura_data.get("nombre"):
                raise Exception("Datos incompletos de cliente")

            # =========================
            # 2. GUARDAR FACTURA
            # =========================
            headers_supabase = {
                "apikey": KEY_SUPABASE,
                "Authorization": f"Bearer {KEY_SUPABASE}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }

            url_api = f"{URL_SUPABASE}/rest/v1/ventas"

            res_db = requests.post(
                url_api,
                json=factura_data,
                headers=headers_supabase
            )

            if res_db.status_code not in [200, 201]:
                raise Exception(f"Error Supabase: {res_db.text}")

            # =========================
            # 3. WHATSAPP BRIDGE
            # =========================
            telefono = factura_data.get("telefono")
            nombre = factura_data.get("nombre", "Cliente")
            id_factura = factura_data.get("id_factura")

            if URL_PUENTE and telefono and telefono != "N/A":

                link_factura = f"https://tu-proyecto.vercel.app/factura.html?id={id_factura}"

                mensaje = (
                    f"👋 Hola *{nombre}*\n\n"
                    f"🧾 Tu factura está lista:\n"
                    f"{link_factura}\n\n"
                    f"Gracias por tu compra ✨"
                )

                payload = {
                    "to": telefono,
                    "message": mensaje
                }

                try:
                    requests.post(
                        f"{URL_PUENTE}/send-message",
                        json=payload,
                        timeout=5
                    )
                except Exception as e:
                    print("⚠️ WhatsApp bridge falló:", e)

            # =========================
            # 4. RESPUESTA
            # =========================
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            self.wfile.write(json.dumps({
                "status": "success",
                "message": "Factura procesada correctamente"
            }).encode('utf-8'))

        except Exception as e:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            self.wfile.write(json.dumps({
                "status": "error",
                "message": str(e)
            }).encode('utf-8'))
