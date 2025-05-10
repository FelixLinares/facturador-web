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

  const pWrap = $("progressWrap"), pBar = $("progressBar");
  const showProg = n => { pWrap.hidden = false; pBar.style.width = n + "%"; }
  const hideProg = () => { pWrap.hidden = true; pBar.style.width = "0"; }

  // Función load corregida
  async function load() {
    try {
      const res = await fetch("/api/patients");
      const data = await res.json();
      const { patients, count, subtotal } = data;

      // Actualiza Total y Subtotal
      totalTxt.textContent    = count;
      subtotalTxt.textContent = `₱${subtotal.toLocaleString()}`;

      // Limpia la tabla
      tbody.innerHTML = "";
      if (!patients.length) {
        tbody.innerHTML = `<tr class="empty"><td colspan="4">No hay pacientes</td></tr>`;
        return;
      }

      // Rellena filas
      patients.forEach(p => {
        const tr = document.createElement("tr");
        tr.className = "fade";
        tr.innerHTML = `
          <td>${p.id}</td>
          <td>${p.name}</td>
          <td>₱${p.price.toLocaleString()}</td>
          <td>
            <button class="btn btn-info btn-sm edit" data-id="${p.id}"><i class="fa fa-pen"></i></button>
            <button class="btn btn-danger btn-sm del"  data-id="${p.id}"><i class="fa fa-trash"></i></button>
          </td>`;
        tbody.appendChild(tr);
      });
    } catch (e) {
      console.error("Error al cargar pacientes", e);
      alert("Error al cargar pacientes");
    }
  }

  // Botón "Agregar Paciente"
  $("addBtn").onclick = () => {
    editID = null;
    nameInp.value = "";
    priceInp.value = "";
    $("modalTitle").textContent = "Nuevo Paciente";
    modal.showModal();
  };

  // Editar / Borrar desde la tabla
  tbody.onclick = e => {
    const btn = e.target.closest("button");
    if (!btn) return;
    const id = btn.dataset.id;
    if (btn.classList.contains("del")) {
      if (confirm("¿Eliminar?")) {
        fetch(`/api/patients/${id}`, { method: "DELETE" })
          .then(() => load());
      }
    } else if (btn.classList.contains("edit")) {
      editID = id;
      const tr = btn.closest("tr").children;
      nameInp.value  = tr[1].textContent;
      priceInp.value = parseInt(tr[2].textContent.replace(/[^\d]/g,"")) || "";
      $("modalTitle").textContent = "Editar Paciente";
      modal.showModal();
    }
  };

  // Formulario modal: Guardar / Cancelar
  $("modalForm").addEventListener("submit", ev => {
    ev.preventDefault();
    if (ev.submitter.value === "cancel") {
      modal.close();
      return;
    }
    const body = { name: nameInp.value.trim() };
    if (priceInp.value) body.price = priceInp.value;
    const url    = editID ? `/api/patients/${editID}` : "/api/patients";
    const method = editID ? "PUT"                 : "POST";

    fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    })
    .then(r => {
      if (!r.ok) throw new Error();
    })
    .then(() => {
      modal.close();
      load();
    })
    .catch(() => alert("Error al guardar paciente"));
  });

  // Vaciar lista
  $("clearBtn").onclick = () => {
    if (confirm("¿Vaciar lista?")) {
      fetch("/api/clear", { method: "DELETE" })
        .then(() => load());
    }
  };

  // Cargar archivos con progreso
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

  // Generar factura (PDF / Word)
  async function gen(fmt) {
    if (tbody.querySelector(".empty")) {
      alert("Sin pacientes");
      return;
    }
    const num = invoiceInput.value.trim() || `FAC-${Date.now().toString().slice(-4)}`;
    try {
      const res = await fetch(`/api/invoice/${fmt}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ invoice_number: num })
      });
      if (!res.ok) throw new Error();
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

  // Número de factura inicial y carga de datos
  invoiceInput.value = `FAC-${new Date().getFullYear()}${("0000"+(Date.now()%10000)).slice(-4)}`;
  load();
});
