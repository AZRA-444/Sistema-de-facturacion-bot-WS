async function cargarFactura() {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("id");

    // Referencias DOM
    const loading = document.getElementById("loading");
    const facturaContainer = document.getElementById("factura");
    const facturaActions = document.getElementById("factura-actions");
    const errorContainer = document.getElementById("factura-error");
    const errorMsg = document.getElementById("factura-error-msg");

    // Funciones de estado
    function mostrarError(msg) {
        loading.style.display = "none";
        facturaContainer.style.display = "none";
        facturaActions.style.display = "none";

        errorContainer.style.display = "block";
        errorMsg.textContent = msg;
    }

    function mostrarFactura() {
        loading.style.display = "none";
        errorContainer.style.display = "none";

        facturaContainer.style.display = "block";
        facturaActions.style.display = "flex";
    }

    if (!id) {
        mostrarError("No se recibió un ID de factura.");
        return;
    }

    const SUPABASE_URL =
        "https://etfdwjbgrbxfuoltpgqa.supabase.co";

    const SUPABASE_ANON_KEY =
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV0ZmR3amJncmJ4ZnVvbHRwZ3FhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI3OTg0NDQsImV4cCI6MjA5ODM3NDQ0NH0.Ap4HsuDjA43fKlTA8DP_ljwIn6vnE_pEw1LiMmFngvU";

    try {
        const headers = {
            apikey: SUPABASE_ANON_KEY,
            Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
            "Content-Type": "application/json"
        };

        // Consultar factura y detalles simultáneamente
        const [resFactura, resDetalles] = await Promise.all([
            fetch(
                `${SUPABASE_URL}/rest/v1/facturas?id_factura=eq.${id}&select=*`,
                { headers }
            ),
            fetch(
                `${SUPABASE_URL}/rest/v1/factura_detalles?id_factura=eq.${id}&select=*`,
                { headers }
            )
        ]);

        if (!resFactura.ok || !resDetalles.ok) {
            throw new Error("No se pudo consultar la factura");
        }

        const facturaData = await resFactura.json();
        const detalles = await resDetalles.json();

        if (!facturaData.length) {
            throw new Error("Factura no encontrada");
        }

        const factura = facturaData[0];

        // =========================
        // DATOS GENERALES
        // =========================

        document.getElementById("id_factura").textContent =
            `N° ${factura.id_factura}`;

        document.getElementById("cliente").textContent =
            `${factura.nombre || ""} ${factura.apellido || ""}`.trim();

        document.getElementById("cedula").textContent =
            factura.cedula || "N/A";

        document.getElementById("telefono").textContent =
            factura.telefono || "N/A";

        document.getElementById("vendedor").textContent =
            factura.vendedor || "N/A";

        document.getElementById("fecha").textContent =
            factura.fecha
                ? new Date(factura.fecha).toLocaleString("es-VE")
                : "N/A";

        // =========================
        // TOTALES
        // =========================

        document.getElementById("subtotal_usd").textContent =
            Number(factura.subtotal_usd || 0).toFixed(2);

        document.getElementById("descuento_usd").textContent =
            Number(factura.descuento_usd || 0).toFixed(2);

        document.getElementById("total_usd").textContent =
            Number(factura.total_usd || 0).toFixed(2);

        document.getElementById("total_bs").textContent =
            Number(factura.total_bs || 0).toFixed(2);

        // =========================
        // PAGO
        // =========================

        document.getElementById("metodo_pago").textContent =
            factura.metodo_pago || "N/A";

        const referenciaInfo =
            document.getElementById("referencia_info");

        if (factura.referencia) {
            referenciaInfo.innerHTML = `
                <strong>Referencia:</strong>
                ${factura.referencia}
                ${factura.banco ? `- ${factura.banco}` : ""}
            `;
        } else {
            referenciaInfo.innerHTML = "";
        }

        // =========================
        // PRODUCTOS
        // =========================

        const tbody =
            document.querySelector("#tabla_productos tbody");

        tbody.innerHTML = "";

        if (detalles.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align:center;">
                        No hay productos registrados
                    </td>
                </tr>
            `;
        } else {
            detalles.forEach(producto => {
                const tr = document.createElement("tr");

                tr.innerHTML = `
                    <td>${producto.cantidad || 0}</td>
                    <td>${producto.nombre_producto || "-"}</td>
                    <td>$${Number(producto.precio_unitario || 0).toFixed(2)}</td>
                    <td>$${Number(producto.precio_total || 0).toFixed(2)}</td>
                `;

                tbody.appendChild(tr);
            });
        }

        // Mostrar contenido
        mostrarFactura();

    } catch (error) {
        console.error(error);

        mostrarError(
            error.message || "Error inesperado al cargar la factura."
        );
    }
}

document.addEventListener(
    "DOMContentLoaded",
    cargarFactura
);
