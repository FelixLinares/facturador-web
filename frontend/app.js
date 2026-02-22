// app.js
document.addEventListener("DOMContentLoaded", () => {
  const $ = id => document.getElementById(id);
  const tbody        = $("tbody");
  const totalTxt     = $("totalTxt");
  const subtotalTxt  = $("subtotalTxt");
  const invoiceInput = $("invoiceInput");

  const modal   = $("modal");
  const nameInp = $("nameInput");
  const priceInp= $("priceInput");
  let editID    = null;

  // ===== EDICIÓN MASIVA =====
  const editPricesBtn   = $("editPricesBtn");
  const editPricesModal = $("editPricesModal");
  const pricesList      = $("pricesList");
  const cancelEditBtn   = $("cancelEditPrices");
  const applyEditBtn    = $("applyEditPrices");
  let cachedPatients    = [];
  // =========================

  const pWrap = $("progressWrap"), pBar = $("progressBar");
  const showProg = n => { pWrap.hidden = false; pBar.style.width = n + "%"; }
  const hideProg = () => { pWrap.hidden = true; pBar.style.width = "0"; }

  // ================= LOAD =================
  async function load() {
    try {
      const res = await fetch("/api/patients");
      const { patients, count, subtotal } = await res.json();

      cachedPatients = patients;

      totalTxt.textContent    = count;
      subtotalTxt.textContent = `₱${subtotal.toLocaleString()}`;

      tbody.innerHTML = "";

      if (!patients.length) {
        tbody.innerHTML = `<tr class="empty"><td colspan="4">No hay pacientes</td></tr>`;
        editPricesBtn.style.display = "none";
        return;
      }

      editPricesBtn.style.display = "inline-flex";

      patients.forEach(p => {
        const tr = document.createElement("tr");
        tr.className = "fade";
        tr.innerHTML = `
          <td>${p.id}</td>
          <td>${p.name}</td>
          <td>₱${p.price.toLocaleString()}</td>
          <td>
            <button class="btn btn-info btn-sm edit" data-id="${p.id}">
              <i class="fa fa-pen"></i>
            </button>
            <button class="btn btn-danger btn-sm del" data-id="${p.id}">
              <i class="fa fa-trash"></i>
            </button>
          </td>`;
        tbody.appendChild(tr);
      });
    } catch (e) {
      console.error(e);
      alert("Error al cargar pacientes");
    }
  }

  // ================= EDICIÓN MASIVA =================
  editPricesBtn.onclick = () => {
    const grupos = {};

    cachedPatients.forEach(p => {
      grupos[p.price] = (grupos[p.price] || 0) + 1;
    });

    pricesList.innerHTML = "";
    Object.keys(grupos).forEach(price => {
      pricesList.innerHTML += `
        <div>
          <strong>${grupos[price]} estudios</strong> a 
          <strong>₱${Number(price).toLocaleString()}</strong>
          <input
            type="number"
            data-old="${price}"
            placeholder="Nuevo precio"
          >
        </div>
      `;
    });

    editPricesModal.style.display = "block";
  };

  cancelEditBtn.onclick = () => {
    editPricesModal.style.display = "none";
  };

  applyEditBtn.onclick = async () => {
    const inputs = pricesList.querySelectorAll("input");
    const updates = [];

    inputs.forEach(inp => {
      const oldPrice = Number(inp.dataset.old);
      const newPrice = Number(inp.value);
      if (newPrice > 0 && newPrice !== oldPrice) {
        cachedPatients
          .filter(p => p.price === oldPrice)
          .forEach(p => updates.push({ id: p.id, price: newPrice }));
      }
    });

    try {
      for (const u of updates) {
        await fetch(`/api/patients/${u.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ price: u.price })
        });
      }
      editPricesModal.style.display = "none";
      load();
    } catch {
      alert("Error al aplicar cambios masivos");
    }
  };
  // ==================================================

  // ===== AGREGAR PACIENTE =====
  $("addBtn").onclick = () => {
    editID = null;
    nameInp.value = "";
    priceInp.value = "";
    $("modalTitle").textContent = "Nuevo Paciente";
    modal.showModal();
  };

  // ===== EDITAR / ELIMINAR =====
  tbody.onclick = e => {
    const btn = e.target.closest("button");
    if (!btn) return;

    const id = btn.dataset.id;

    if (btn.classList.contains("del")) {
      if (confirm("¿Eliminar?")) {
        fetch(`/api/patients/${id}`, { method: "DELETE" })
          .then(() => load());
      }
    }

    if (btn.classList.contains("edit")) {
      editID = id;
      const tr = btn.closest("tr").children;
      nameInp.value  = tr[1].textContent;
      priceInp.value = Number(tr[2].textContent.replace(/[^\d]/g, ""));
      $("modalTitle").textContent = "Editar Paciente";
      modal.showModal();
    }
  };

  // ===== GUARDAR PACIENTE (CORREGIDO) =====
  $("modalForm").addEventListener("submit", ev => {
    ev.preventDefault();

    if (ev.submitter.value === "cancel") {
      modal.close();
      return;
    }

    const body = { name: nameInp.value.trim() };

    if (priceInp.value !== "") {
      body.price = Number(priceInp.value);
    }

    const url    = editID ? `/api/patients/${editID}` : "/api/patients";
    const method = editID ? "PUT" : "POST";

    fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    })
    .then(() => {
      modal.close();
      load();
    })
    .catch(() => alert("Error al guardar paciente"));
  });

  // ===== VACIAR LISTA =====
  $("clearBtn").onclick = () => {
    if (confirm("¿Vaciar lista?")) {
      fetch("/api/clear", { method: "DELETE" })
        .then(() => load());
    }
  };

  // ===== CARGA DE ARCHIVOS =====
  $("uploadBtn").onclick = () => $("fileInput").click();
  $("fileInput").onchange = () => {
    const fd = new FormData();
    [...$("fileInput").files].forEach(f => fd.append("files", f));
    const xhr = new XMLHttpRequest();
    xhr.upload.onprogress = e => showProg(Math.round(e.loaded * 100 / e.total));
    xhr.onload = () => {
      hideProg();
      load();
      $("fileInput").value = "";
    };
    xhr.onerror = () => {
      hideProg();
      alert("Error al cargar archivos");
    };
    xhr.open("POST", "/api/patients");
    xhr.send(fd);
  };

  // ===== FACTURACIÓN =====
  async function gen(fmt) {
    if (tbody.querySelector(".empty")) {
      alert("Sin pacientes");
      return;
    }

    const num = invoiceInput.value.trim()
      || `FAC-${new Date().getFullYear()}${("0000"+(Date.now()%10000)).slice(-4)}`;

    try {
      const res = await fetch(`/api/invoice/${fmt}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ invoice_number: num })
      });

      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `Factura_${num}.${fmt === "word" ? "docx" : "pdf"}`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 100);
    } catch {
      alert("Error al generar factura");
    }
  }

  $("pdfBtn").onclick  = () => gen("pdf");
  $("docxBtn").onclick = () => gen("word");

  invoiceInput.value =
    `FAC-${new Date().getFullYear()}${("0000"+(Date.now()%10000)).slice(-4)}`;

  load();
});

