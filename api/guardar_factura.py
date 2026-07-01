from http.server import BaseHTTPRequestHandler
import json
import os
import requests
from datetime import datetime
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

URL_SUPABASE = os.environ.get("SUPABASE_URL", "")
KEY_SUPABASE = os.environ.get("SUPABASE_SECRET_KEY", "")
URL_PUENTE = os.environ.get("URL_PUENTE_WHATSAPP", "")
SUPABASE_BUCKET = "facturas"

headers_supabase = {
    "apikey": KEY_SUPABASE,
    "Authorization": f"Bearer {KEY_SUPABASE}",
    "Content-Type": "application/json"
}

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    # =========================
    # 🧾 GENERAR PDF EN MEMORIA
    # =========================
    def generar_pdf(self, factura):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer)

        styles = getSampleStyleSheet()
        contenido = []

        contenido.append(Paragraph("FACTURA DE COMPRA", styles["Title"]))
        contenido.append(Spacer(1, 12))

        # INFO CLIENTE
        cliente_info = [
            ["Cliente", f"{factura['nombre']} {factura['apellido']}"],
            ["Cédula", factura["cedula"]],
            ["Teléfono", factura["telefono"]],
            ["Vendedor", factura["vendedor"]],
            ["Fecha", str(datetime.now())]
        ]

        tabla_cliente = Table(cliente_info)
        tabla_cliente.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
        ]))

        contenido.append(tabla_cliente)
        contenido.append(Spacer(1, 20))

        # PRODUCTOS
        productos = [["Producto", "Cant", "P/U", "Total"]]

        for p in factura.get("productos", []):
            productos.append([
                p["nombre"],
                str(p["cantidad"]),
                f"${p['precioUnitario']}",
                f"${p['precioTotal']}"
            ])

        tabla_prod = Table(productos)
        tabla_prod.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)
        ]))

        contenido.append(tabla_prod)
        contenido.append(Spacer(1, 20))

        # TOTALES
        totales = [
            ["Subtotal USD", factura["subtotal_usd"]],
            ["Descuento", factura["descuento_usd"]],
            ["TOTAL USD", factura["total_usd"]]
        ]

        tabla_totales = Table(totales)
        tabla_totales.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
        ]))

        contenido.append(tabla_totales)

        doc.build(contenido)
        buffer.seek(0)

        return buffer

    # =========================
    # ⬆ SUBIR PDF A SUPABASE
    # =========================
    def subir_pdf(self, buffer, factura_id):
        filename = f"{factura_id}.pdf"

        url = f"{URL_SUPABASE}/storage/v1/object/{SUPABASE_BUCKET}/{filename}"

        headers = {
            "apikey": KEY_SUPABASE,
            "Authorization": f"Bearer {KEY_SUPABASE}",
            "Content-Type": "application/pdf"
        }

        r = requests.post(url, data=buffer.read(), headers=headers)

        if r.status_code not in [200, 201]:
            raise Exception(f"Error subiendo PDF: {r.text}")

        public_url = f"{URL_SUPABASE}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename}"

        return public_url

    # =========================
    # POST MAIN
    # =========================
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            factura_data = json.loads(post_data.decode('utf-8'))

            # =========================
            # 1. GUARDAR EN SUPABASE
            # =========================
            url_api = f"{URL_SUPABASE}/rest/v1/ventas"

            res_db = requests.post(
                url_api,
                json=factura_data,
                headers=headers_supabase
            )

            if res_db.status_code not in [200, 201]:
                raise Exception(res_db.text)

            # =========================
            # 2. GENERAR PDF
            # =========================
            pdf_buffer = self.generar_pdf(factura_data)

            # =========================
            # 3. SUBIR PDF
            # =========================
            factura_id = factura_data.get("id_factura", str(datetime.now().timestamp()))

            pdf_url = self.subir_pdf(pdf_buffer, factura_id)

            # =========================
            # 4. WHATSAPP
            # =========================
            telefono = factura_data.get("telefono")
            nombre = factura_data.get("nombre", "Cliente")

            if URL_PUENTE and telefono and telefono != "N/A":

                mensaje = (
                    f"👋 Hola *{nombre}*\n\n"
                    f"🧾 Tu factura está lista:\n"
                    f"🔗 {pdf_url}\n\n"
                    f"Gracias por tu compra ✨"
                )

                requests.post(
                    f"{URL_PUENTE}/send-message",
                    json={
                        "to": telefono,
                        "message": mensaje
                    },
                    timeout=5
                )

            # =========================
            # RESPONSE
            # =========================
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            self.wfile.write(json.dumps({
                "status": "success",
                "pdf_url": pdf_url
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
