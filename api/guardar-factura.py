from http.server import BaseHTTPRequestHandler
import json
import os
import requests

URL_SUPABASE = os.environ.get("SUPABASE_URL", "")
KEY_SUPABASE = os.environ.get("SUPABASE_SECRET_KEY", "")
# Configura tu dominio real aquí o usa la variable de entorno FRONTEND_DOMAIN
FRONTEND_DOMAIN = os.environ.get("FRONTEND_DOMAIN", "https://sistema-de-facturacion-bot-ws.vercel.app")

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
            
            # ========================================================
            # 1. Guardado distribuido en la Base de Datos (Dos Tablas)
            # ========================================================
            headers_supabase = {
                "apikey": KEY_SUPABASE,
                "Authorization": f"Bearer {KEY_SUPABASE}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
            
            # TABLA A: Cabecera de la Factura
            factura_payload = {
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
            
            url_facturas = f"{URL_SUPABASE}/rest/v1/facturas"
            res_factura = requests.post(url_facturas, json=factura_payload, headers=headers_supabase, timeout=10)
            
            if res_factura.status_code not in [200, 201]:
                raise Exception(f"Error de Supabase (Facturas): {res_factura.text}")
            
            # TABLA B: Detalles de la Factura (Productos)
            detalles = []
            for p in factura_data.get("productos", []):
                detalles.append({
                    "id_factura": factura_data.get("id_factura"),
                    "nombre_producto": p.get("nombre") or p.get("nombre_producto"),
                    "cantidad": p.get("cantidad"),
                    "precio_unitario": p.get("precioUnitario") or p.get("precio_unitario"),
                    "precio_total": p.get("precioTotal") or p.get("precio_total")
                })
            
            if detalles:
                url_detalles = f"{URL_SUPABASE}/rest/v1/factura_detalles"
                res_detalles = requests.post(url_detalles, json=detalles, headers=headers_supabase, timeout=10)
                if res_detalles.status_code not in [200, 201]:
                    print(f"⚠️ Alerta: No se guardaron los detalles de los productos: {res_detalles.text}")

            # ========================================================
            # 2. Envío al Puente Local de WhatsApp (Lógica Intacta)
            # ========================================================
            URL_PUENTE = os.environ.get("URL_PUENTE", "")
            telefono_cliente = factura_data.get("telefono")
            nombre_cliente = factura_data.get("nombre", "Cliente")
            id_factura = factura_data.get("id_factura")
            
            if URL_PUENTE and telefono_cliente and telefono_cliente != "N/A":
                link_factura = f"{FRONTEND_DOMAIN}/assets/pages/factura.html?id={id_factura}"
                
                payload_puente = {
                    "to": telefono_cliente,
                    "message": f"👋 ¡Hola, *{nombre_cliente}*!\n\nAquí tienes el link de tu factura digital:\n🔗 {link_factura}\n\n¡Gracias por tu compra! ✨"
                }
                
                try:
                    # El .rstrip('/') previene errores por barras consecutivas si la ENV trae un / al final
                    url_endpoint_puente = f"{URL_PUENTE.rstrip('/')}/send-message"
                    requests.post(url_endpoint_puente, json=payload_puente, timeout=4)
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
