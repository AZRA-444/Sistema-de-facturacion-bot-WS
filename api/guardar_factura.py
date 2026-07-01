from http.server import BaseHTTPRequestHandler
import json
import os
import requests

URL_SUPABASE = os.environ.get("SUPABASE_URL", "")
KEY_SUPABASE = os.environ.get("SUPABASE_SECRET_KEY", "")

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
            
            # 1. Guardado directo en la base de datos (Supabase)
            headers_supabase = {
                "apikey": KEY_SUPABASE,
                "Authorization": f"Bearer {KEY_SUPABASE}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
            url_api = f"{URL_SUPABASE}/rest/v1/ventas"
            res_db = requests.post(url_api, json=factura_data, headers=headers_supabase)
            
            if res_db.status_code not in [200, 201]:
                raise Exception(f"Error de Supabase: {res_db.text}")
            
            # 2. Envío al Puente Local de WhatsApp
            URL_PUENTE = os.environ.get("URL_PUENTE", "")
            telefono_cliente = factura_data.get("telefono")
            nombre_cliente = factura_data.get("nombre", "Cliente")
            id_factura = factura_data.get("id_factura")
            
            if URL_PUENTE and telefono_cliente and telefono_cliente != "N/A":
                link_factura = f"https://sistema-de-facturacion-bot-ws.vercel.app/factura.html?id={id_factura}"
                
                payload_puente = {
                    "to": telefono_cliente,
                    "message": f"👋 ¡Hola, *{nombre_cliente}*!\n\nAquí tienes el link de tu factura digital:\n🔗 {link_factura}\n\n¡Gracias por tu compra! ✨"
                }
                
                try:
                    requests.post(f"{URL_PUENTE}/send-message", json=payload_puente, timeout=4)
                except Exception as ws_err:
                    print(f"⚠️ Alerta: El puente no procesó el mensaje: {ws_err}")

            # 3. Respuesta exitosa al Frontend
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*') 
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "Proceso completado"}).encode('utf-8'))
            
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
