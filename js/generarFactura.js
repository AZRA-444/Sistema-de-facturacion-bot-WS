    async function cargarFactura() {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');

    if (!id) return;

    const SUPABASE_URL = 'https://etfdwjbgrbxfuoltpgqa.supabase.co';
    const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV0ZmR3amJncmJ4ZnVvbHRwZ3FhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI3OTg0NDQsImV4cCI6MjA5ODM3NDQ0NH0.Ap4HsuDjA43fKlTA8DP_ljwIn6vnE_pEw1LiMmFngvU';

    try {
        // Opción 1: Simple
        const [resFactura, resDetalles] = await Promise.all([
        fetch(`${SUPABASE_URL}/rest/v1/facturas?id_factura=eq.${id}&select=*`, {
            headers: {
            'apikey': SUPABASE_ANON_KEY,
            'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
            }
        }),
        fetch(`${SUPABASE_URL}/rest/v1/factura_detalles?id_factura=eq.${id}&select=*`, {
            headers: {
            'apikey': SUPABASE_ANON_KEY,
            'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
            }
        })
        ]);

        const factura = (await resFactura.json())[0];
        const detalles = await resDetalles.json();

        // Renderizar
        document.getElementById('id_factura').textContent = `N° ${factura.id_factura}`;
        document.getElementById('cliente').textContent = `${factura.nombre} ${factura.apellido || ''}`;
        document.getElementById('cedula').textContent = factura.cedula || 'N/A';
        document.getElementById('telefono').textContent = factura.telefono;
        document.getElementById('vendedor').textContent = factura.vendedor || 'N/A';
        document.getElementById('fecha').textContent = new Date(factura.fecha).toLocaleString('es-VE');

        document.getElementById('subtotal_usd').textContent = factura.subtotal_usd?.toFixed(2) || '0.00';
        document.getElementById('descuento_usd').textContent = factura.descuento_usd?.toFixed(2) || '0.00';
        document.getElementById('total_usd').textContent = factura.total_usd?.toFixed(2) || '0.00';
        document.getElementById('total_bs').textContent = factura.total_bs?.toFixed(2) || '0.00';

        document.getElementById('metodo_pago').textContent = factura.metodo_pago || 'N/A';
        if (factura.referencia) {
          document.getElementById('referencia_info').textContent = `Referencia: ${factura.referencia} - ${factura.banco || ''}`;
        }

        // Productos
        const tbody = document.querySelector('#tabla_productos tbody');
        tbody.innerHTML = '';
        detalles.forEach(d => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td>${d.nombre_producto}</td>
            <td>${d.cantidad}</td>
            <td>$${d.precio_unitario}</td>
            <td>$${d.precio_total}</td>
          `;
          tbody.appendChild(tr);
        });

      } catch (e) {
        document.getElementById('factura').innerHTML = `<h2>Error: ${e.message}</h2>`;
      }
    }

    window.onload = cargarFactura;