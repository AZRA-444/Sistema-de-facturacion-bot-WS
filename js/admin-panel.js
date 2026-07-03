// ============================================================
// CONFIGURACIÓN SUPABASE — mismos valores que usas en factura.js
// ============================================================
const SUPABASE_URL = "https://etfdwjbgrbxfuoltpgqa.supabase.co";
const SUPABASE_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV0ZmR3amJncmJ4ZnVvbHRwZ3FhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI3OTg0NDQsImV4cCI6MjA5ODM3NDQ0NH0.Ap4HsuDjA43fKlTA8DP_ljwIn6vnE_pEw1LiMmFngvU";

// NOTA IMPORTANTE: cambia esto si tu columna de fecha se llama distinto.
const COL_FECHA = "created_at";

const headers = {
  apikey: SUPABASE_ANON_KEY,
  Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
  "Content-Type": "application/json",
};

function fmtUSD(n) {
  return (
    "$" +
    (Number(n) || 0).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}
function fmtBS(n) {
  return (Number(n) || 0).toLocaleString("es-VE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}
function fmtFecha(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  return (
    d.toLocaleDateString("es-VE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }) +
    " " +
    d.toLocaleTimeString("es-VE", { hour: "2-digit", minute: "2-digit" })
  );
}

// ============================================================
// RELOJ
// ============================================================
function tickClock() {
  document.getElementById("clock").textContent = new Date().toLocaleString(
    "es-VE",
    {
      weekday: "long",
      day: "2-digit",
      month: "short",
      year: "numeric",
    },
  );
}
tickClock();
setInterval(tickClock, 30000);

// ============================================================
// TABS
// ============================================================
document.querySelectorAll(".ledger-tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document
      .querySelectorAll(".ledger-tabs button")
      .forEach((b) => b.classList.remove("active"));
    document
      .querySelectorAll(".panel")
      .forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document
      .getElementById("panel-" + btn.dataset.panel)
      .classList.add("active");
  });
});

// ============================================================
// FILTROS — construye la query de Supabase (PostgREST)
// ============================================================
function primerDiaDelMes(mesStr) {
  return mesStr + "-01T00:00:00";
}
function primerDiaSiguienteMes(mesStr) {
  const [y, m] = mesStr.split("-").map(Number);
  const next =
    m === 12 ? `${y + 1}-01` : `${y}-${String(m + 1).padStart(2, "0")}`;
  return next + "-01T00:00:00";
}

async function buscarFacturas() {
  const mes = document.getElementById("f-mes").value;
  const dia = document.getElementById("f-dia").value;
  const cedula = document.getElementById("f-cedula").value.trim();
  const vendedor = document.getElementById("f-vendedor").value.trim();
  const idFactura = document.getElementById("f-id").value.trim();
  const metodo = document.getElementById("f-metodo").value;

  const statusEl = document.getElementById("status-ventas");
  statusEl.textContent = "Cargando…";
  statusEl.classList.remove("error");

  let query = `${SUPABASE_URL}/rest/v1/facturas?select=*&order=${COL_FECHA}.desc`;

  if (dia) {
    const start = dia + "T00:00:00";
    const end = new Date(new Date(dia).getTime() + 86400000)
      .toISOString()
      .slice(0, 19);
    query += `&${COL_FECHA}=gte.${start}&${COL_FECHA}=lt.${end}`;
  } else if (mes) {
    query += `&${COL_FECHA}=gte.${primerDiaDelMes(mes)}&${COL_FECHA}=lt.${primerDiaSiguienteMes(mes)}`;
  }
  if (cedula) query += `&cedula=eq.${encodeURIComponent(cedula)}`;
  if (vendedor) query += `&vendedor=ilike.*${encodeURIComponent(vendedor)}*`;
  if (idFactura)
    query += `&id_factura=ilike.*${encodeURIComponent(idFactura)}*`;
  if (metodo) query += `&metodo_pago=eq.${encodeURIComponent(metodo)}`;

  try {
    const res = await fetch(query, { headers });
    if (!res.ok)
      throw new Error("Error " + res.status + " al consultar facturas");
    const data = await res.json();
    statusEl.textContent = `Actualizado ${new Date().toLocaleTimeString("es-VE")}`;
    renderVentas(data);
  } catch (err) {
    statusEl.textContent = "No se pudo cargar: " + err.message;
    statusEl.classList.add("error");
    renderVentas([]);
  }
}

function renderVentas(facturas) {
  const tbody = document.getElementById("tbody-ventas");
  const empty = document.getElementById("empty-ventas");
  tbody.innerHTML = "";
  document.getElementById("ventas-count-label").textContent =
    `(${facturas.length} registros)`;

  if (!facturas.length) {
    empty.style.display = "block";
  } else {
    empty.style.display = "none";
    facturas.forEach((f) => {
      const subtotal =
        (Number(f.total_usd) || 0) + (Number(f.descuento_usd) || 0);
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${f.id_factura}</td>
        <td>${fmtFecha(f[COL_FECHA])}</td>
        <td>${f.nombre || ""} ${f.apellido || ""}</td>
        <td>${f.cedula || ""}</td>
        <td>${f.vendedor || ""}</td>
        <td><span class="tag">${f.metodo_pago || "-"}</span></td>
        <td class="num">${fmtUSD(subtotal)}</td>
        <td class="num">${fmtUSD(f.descuento_usd)}</td>
        <td class="num">${fmtUSD(f.total_usd)}</td>
        <td class="num">${fmtBS(f.total_bs)}</td>
        <td>
          <button class="btn small ghost" onclick="verDetalle('${f.id_factura}')">Ver</button>
          <button class="btn small" onclick="abrirDescuento('${f.id_factura}', ${subtotal}, ${Number(f.descuento_usd) || 0}, ${Number(f.subtotal_bs) || f.total_bs || 0}, ${Number(f.descuento_bs) || 0})">Descuento</button>
        </td>`;
      tbody.appendChild(tr);
    });
  }

  renderKPIs(facturas);
  renderCharts(facturas);
  window.__facturasActuales = facturas; // cache para modales
}

function renderKPIs(facturas) {
  const totalUSD = facturas.reduce((s, f) => s + (Number(f.total_usd) || 0), 0);
  const totalBS = facturas.reduce((s, f) => s + (Number(f.total_bs) || 0), 0);
  const totalDesc = facturas.reduce(
    (s, f) => s + (Number(f.descuento_usd) || 0),
    0,
  );
  document.getElementById("kpi-usd").textContent = fmtUSD(totalUSD);
  document.getElementById("kpi-bs").textContent = fmtBS(totalBS);
  document.getElementById("kpi-count").textContent = facturas.length;
  document.getElementById("kpi-avg").textContent = fmtUSD(
    facturas.length ? totalUSD / facturas.length : 0,
  );
  document.getElementById("kpi-desc").textContent = fmtUSD(totalDesc);
}

// ============================================================
// GRÁFICAS
// ============================================================
let chartDias, chartVendedores, chartMetodos;

function renderCharts(facturas) {
  const porDia = {};
  const porVendedor = {};
  const porMetodo = {};

  facturas.forEach((f) => {
    const fecha = f[COL_FECHA] ? f[COL_FECHA].slice(0, 10) : "s/f";
    porDia[fecha] = (porDia[fecha] || 0) + (Number(f.total_usd) || 0);

    const v = f.vendedor || "Sin asignar";
    porVendedor[v] = (porVendedor[v] || 0) + (Number(f.total_usd) || 0);

    const m = f.metodo_pago || "Otro";
    porMetodo[m] = (porMetodo[m] || 0) + 1;
  });

  const diasLabels = Object.keys(porDia).sort();
  const paletteLine = "#0f6e63";
  const paletteBars = [
    "#0f6e63",
    "#c8781f",
    "#a8352a",
    "#3f5b6b",
    "#7a8c5c",
    "#8a6d3b",
  ];

  if (chartDias) chartDias.destroy();
  chartDias = new Chart(document.getElementById("chart-dias"), {
    type: "bar",
    data: {
      labels: diasLabels,
      datasets: [
        {
          label: "USD",
          data: diasLabels.map((d) => porDia[d]),
          backgroundColor: paletteLine,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });

  const vendLabels = Object.keys(porVendedor)
    .sort((a, b) => porVendedor[b] - porVendedor[a])
    .slice(0, 8);
  if (chartVendedores) chartVendedores.destroy();
  chartVendedores = new Chart(document.getElementById("chart-vendedores"), {
    type: "bar",
    data: {
      labels: vendLabels,
      datasets: [
        {
          label: "USD",
          data: vendLabels.map((v) => porVendedor[v]),
          backgroundColor: paletteBars,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      plugins: { legend: { display: false } },
    },
  });

  const metLabels = Object.keys(porMetodo);
  if (chartMetodos) chartMetodos.destroy();
  chartMetodos = new Chart(document.getElementById("chart-metodos"), {
    type: "doughnut",
    data: {
      labels: metLabels,
      datasets: [
        {
          data: metLabels.map((m) => porMetodo[m]),
          backgroundColor: paletteBars,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: "bottom",
          labels: { boxWidth: 10, font: { size: 10 } },
        },
      },
    },
  });
}

// ============================================================
// MODAL DETALLE
// ============================================================
async function verDetalle(idFactura) {
  const factura = (window.__facturasActuales || []).find(
    (f) => f.id_factura === idFactura,
  );
  document.getElementById("modal-detalle-title").textContent =
    "Factura " + idFactura;
  const body = document.getElementById("modal-detalle-body");
  body.innerHTML = "<p>Cargando productos…</p>";
  document.getElementById("modal-detalle").classList.add("active");

  let productosHtml = "<p>No se pudieron cargar los productos.</p>";
  try {
    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/factura_detalles?id_factura=eq.${idFactura}&select=*`,
      { headers },
    );
    if (res.ok) {
      const productos = await res.json();
      productosHtml = productos.length
        ? productos
            .map(
              (p) =>
                `<div class="row"><span>${p.cantidad} × ${p.nombre}</span><span class="num">${fmtUSD(p.precioTotal)}</span></div>`,
            )
            .join("")
        : "<p>Sin productos registrados.</p>";
    }
  } catch (e) {
    /* deja el mensaje de error por defecto */
  }

  body.innerHTML = `
    <div class="row"><span>Cliente</span><span>${factura?.nombre || ""} ${factura?.apellido || ""}</span></div>
    <div class="row"><span>Cédula</span><span>${factura?.cedula || ""}</span></div>
    <div class="row"><span>Teléfono</span><span>${factura?.telefono || ""}</span></div>
    <div class="row"><span>Vendedor</span><span>${factura?.vendedor || ""}</span></div>
    <div class="row"><span>Método de pago</span><span>${factura?.metodo_pago || ""}</span></div>
    <div class="row"><span>Referencia</span><span>${factura?.referencia || ""}</span></div>
    <div class="row"><span>Banco</span><span>${factura?.banco || ""}</span></div>
    <h4 style="margin:14px 0 6px; font-family:var(--serif);">Productos</h4>
    ${productosHtml}
    <div class="row" style="border-top:2px solid var(--ink); margin-top:8px; font-weight:700;">
      <span>Total</span><span class="num">${fmtUSD(factura?.total_usd)} · Bs ${fmtBS(factura?.total_bs)}</span>
    </div>`;
}
document.getElementById("modal-detalle-close").addEventListener("click", () => {
  document.getElementById("modal-detalle").classList.remove("active");
});

// ============================================================
// MODAL EDITAR DESCUENTO
// ============================================================
let descuentoCtx = {};
function abrirDescuento(
  idFactura,
  subtotalUSD,
  descActualUSD,
  subtotalBS,
  descActualBS,
) {
  descuentoCtx = { idFactura, subtotalUSD, subtotalBS };
  document.getElementById("desc-subtotal").value = fmtUSD(subtotalUSD);
  document.getElementById("desc-nuevo").value = descActualUSD.toFixed(2);
  document.getElementById("desc-nuevo-bs").value = descActualBS.toFixed(2);
  document.getElementById("modal-descuento").classList.add("active");
}
document
  .getElementById("modal-descuento-close")
  .addEventListener("click", () => {
    document.getElementById("modal-descuento").classList.remove("active");
  });
document.getElementById("desc-cancelar").addEventListener("click", () => {
  document.getElementById("modal-descuento").classList.remove("active");
});
document.getElementById("desc-guardar").addEventListener("click", async () => {
  const nuevoDescUSD = Number(document.getElementById("desc-nuevo").value) || 0;
  const nuevoDescBS =
    Number(document.getElementById("desc-nuevo-bs").value) || 0;
  const nuevoTotalUSD = Math.max(descuentoCtx.subtotalUSD - nuevoDescUSD, 0);
  const nuevoTotalBS = Math.max(
    (descuentoCtx.subtotalBS || 0) - nuevoDescBS,
    0,
  );

  try {
    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/facturas?id_factura=eq.${descuentoCtx.idFactura}`,
      {
        method: "PATCH",
        headers: { ...headers, Prefer: "return=representation" },
        body: JSON.stringify({
          descuento_usd: nuevoDescUSD,
          total_usd: nuevoTotalUSD,
          descuento_bs: nuevoDescBS,
          total_bs: nuevoTotalBS,
        }),
      },
    );
    if (!res.ok) throw new Error("Error " + res.status);
    document.getElementById("modal-descuento").classList.remove("active");
    buscarFacturas();
  } catch (err) {
    alert("No se pudo actualizar el descuento: " + err.message);
  }
});

// ============================================================
// COMISIONES (1% por venta)
// ============================================================
const COMISION_PORCENTAJE = 0.01;

async function calcularComisiones() {
  const mes = document.getElementById("c-mes").value;
  const statusEl = document.getElementById("status-comisiones");
  if (!mes) {
    statusEl.textContent = "Selecciona un mes.";
    return;
  }

  statusEl.textContent = "Calculando…";
  statusEl.classList.remove("error");

  const query = `${SUPABASE_URL}/rest/v1/facturas?select=vendedor,total_usd&${COL_FECHA}=gte.${primerDiaDelMes(mes)}&${COL_FECHA}=lt.${primerDiaSiguienteMes(mes)}`;

  try {
    const res = await fetch(query, { headers });
    if (!res.ok) throw new Error("Error " + res.status);
    const data = await res.json();
    statusEl.textContent = `Actualizado ${new Date().toLocaleTimeString("es-VE")}`;

    const porVendedor = {};
    data.forEach((f) => {
      const v = f.vendedor || "Sin asignar";
      if (!porVendedor[v]) porVendedor[v] = { ventas: 0, total: 0 };
      porVendedor[v].ventas += 1;
      porVendedor[v].total += Number(f.total_usd) || 0;
    });

    renderComisiones(porVendedor, mes);
  } catch (err) {
    statusEl.textContent = "No se pudo calcular: " + err.message;
    statusEl.classList.add("error");
  }
}

function pagoKey(vendedor, mes) {
  return `comision_pagada__${mes}__${vendedor}`;
}

function renderComisiones(porVendedor, mes) {
  const tbody = document.getElementById("tbody-comisiones");
  const empty = document.getElementById("empty-comisiones");
  tbody.innerHTML = "";

  const vendedores = Object.keys(porVendedor);
  if (!vendedores.length) {
    empty.style.display = "block";
    document.getElementById("kpi-com-total").textContent = fmtUSD(0);
    document.getElementById("kpi-com-vend").textContent = 0;
    document.getElementById("kpi-com-pend").textContent = fmtUSD(0);
    return;
  }
  empty.style.display = "none";

  let totalComisiones = 0,
    pendiente = 0;

  vendedores
    .sort((a, b) => porVendedor[b].total - porVendedor[a].total)
    .forEach((v) => {
      const comision = porVendedor[v].total * COMISION_PORCENTAJE;
      totalComisiones += comision;
      const pagada = localStorage.getItem(pagoKey(v, mes)) === "1";
      if (!pagada) pendiente += comision;

      const tr = document.createElement("tr");
      tr.innerHTML = `
      <td>${v}</td>
      <td class="num">${porVendedor[v].ventas}</td>
      <td class="num">${fmtUSD(porVendedor[v].total)}</td>
      <td class="num">${fmtUSD(comision)}</td>
      <td><span class="tag ${pagada ? "" : "pend"}">${pagada ? "Pagada" : "Pendiente"}</span></td>
      <td><button class="btn small ${pagada ? "ghost" : ""}" data-v="${v}" data-mes="${mes}" onclick="togglePago(this)">${pagada ? "Marcar pendiente" : "Marcar pagada"}</button></td>`;
      tbody.appendChild(tr);
    });

  document.getElementById("kpi-com-total").textContent =
    fmtUSD(totalComisiones);
  document.getElementById("kpi-com-vend").textContent = vendedores.length;
  document.getElementById("kpi-com-pend").textContent = fmtUSD(pendiente);
}

function togglePago(btn) {
  const v = btn.dataset.v,
    mes = btn.dataset.mes;
  const key = pagoKey(v, mes);
  const actual = localStorage.getItem(key) === "1";
  if (actual) localStorage.removeItem(key);
  else localStorage.setItem(key, "1");
  calcularComisiones();
}

// ============================================================
// EVENTOS Y ARRANQUE
// ============================================================
document.getElementById("btn-buscar").addEventListener("click", buscarFacturas);
document.getElementById("btn-limpiar").addEventListener("click", () => {
  ["f-mes", "f-dia", "f-cedula", "f-vendedor", "f-id"].forEach(
    (id) => (document.getElementById(id).value = ""),
  );
  document.getElementById("f-metodo").value = "";
  buscarFacturas();
});
document
  .getElementById("btn-buscar-com")
  .addEventListener("click", calcularComisiones);

(function init() {
  const hoy = new Date();
  const mesActual = hoy.toISOString().slice(0, 7);
  document.getElementById("f-mes").value = mesActual;
  document.getElementById("c-mes").value = mesActual;
  buscarFacturas();
  calcularComisiones();
})();
