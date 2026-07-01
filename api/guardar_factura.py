from flask import Flask, request, jsonify
import requests
import uuid
from datetime import datetime

app = Flask(__name__)

SUPABASE_URL = "TU_SUPABASE_URL"
SUPABASE_KEY = "TU_SUPABASE_KEY"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

@app.route("/api/guardar_factura", methods=["POST"])
def guardar_factura():
    try:
        data = request.json

        # =========================
        # 1. ID ÚNICO DE FACTURA
        # =========================
        factura_id = data.get("id_factura", str(uuid.uuid4()))

        # =========================
        # 2. FACTURA PRINCIPAL
        # =========================
        factura = {
            "id": factura_id,
            "vendedor": data.get("vendedor"),
            "cliente": data.get("nombre"),
            "apellido": data.get("apellido"),
            "cedula": data.get("cedula"),
            "telefono": data.get("telefono"),

            "subtotal_usd": data.get("subtotal_usd"),
            "subtotal_bs": data.get("subtotal_bs"),
            "descuento_usd": data.get("descuento_usd"),
            "descuento_bs": data.get("descuento_bs"),
            "total_usd": data.get("total_usd"),
            "total_bs": data.get("total_bs"),

            "metodo_pago": data.get("metodo_pago"),
            "referencia": data.get("referencia"),
            "banco": data.get("banco"),
            "monto_recibido": data.get("monto_recibido"),
            "vuelto_entregado": data.get("vuelto_entregado"),
            "observaciones": data.get("observaciones"),

            "fecha": datetime.now().isoformat()
        }

        r1 = requests.post(
            f"{SUPABASE_URL}/rest/v1/facturas",
            headers=headers,
            json=factura
        )

        if r1.status_code >= 300:
            return jsonify({
                "status": "error",
                "message": "Error guardando factura",
                "detalle": r1.text
            }), 500

        # =========================
        # 3. PRODUCTOS (MUY IMPORTANTE)
        # =========================
        productos = data.get("productos", [])

        items = []
        for p in productos:
            items.append({
                "factura_id": factura_id,
                "nombre": p["nombre"],
                "cantidad": p["cantidad"],
                "precio_unitario": p["precioUnitario"],
                "precio_unitario_bs": p.get("precioUnitarioBS", 0),
                "precio_total": p["precioTotal"],
                "precio_total_bs": p.get("precioTotalBS", 0)
            })

        if items:
            r2 = requests.post(
                f"{SUPABASE_URL}/rest/v1/factura_items",
                headers=headers,
                json=items
            )

            if r2.status_code >= 300:
                return jsonify({
                    "status": "error",
                    "message": "Factura guardada pero error en productos",
                    "detalle": r2.text
                }), 500

        # =========================
        # 4. RESPUESTA FINAL
        # =========================
        return jsonify({
            "status": "success",
            "factura_id": factura_id
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True)
