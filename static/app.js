const STORAGE_KEY = "gtu_last_downloads_v1";
const MAX_ITEMS = 5;

const formPdf = document.getElementById("generador-form");
const submitPdfBtn = document.getElementById("submit-btn");
const spinnerPdf = submitPdfBtn.querySelector(".spinner");
const labelPdf = submitPdfBtn.querySelector(".btn-label");
const errorPdf = document.getElementById("error-message");

const formSnig = document.getElementById("snig-form");
const submitSnigBtn = document.getElementById("snig-submit-btn");
const spinnerSnig = document.getElementById("snig-spinner");
const labelSnig = document.getElementById("snig-btn-label");
const errorSnig = document.getElementById("snig-error-message");

const historyBody = document.getElementById("history-body");
const toast = document.getElementById("toast");

function loadHistory() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        const items = raw ? JSON.parse(raw) : [];
        return Array.isArray(items) ? items : [];
    } catch (err) {
        return [];
    }
}

function saveHistory(items) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, MAX_ITEMS)));
}

function renderHistory() {
    const items = loadHistory();

    if (!items.length) {
        historyBody.innerHTML = '<tr><td colspan="2" class="empty-row">Aún no hay descargas registradas.</td></tr>';
        return;
    }

    historyBody.innerHTML = items
        .map((item) => {
            const fecha = new Date(item.timestamp).toLocaleString("es-UY");
            return `<tr><td>${item.filename}</td><td>${fecha}</td></tr>`;
        })
        .join("");
}

function pushHistory(filename) {
    const next = [{ filename, timestamp: new Date().toISOString() }, ...loadHistory()].slice(0, MAX_ITEMS);
    saveHistory(next);
    renderHistory();
}

function showToast(message, isError) {
    toast.textContent = message;
    toast.classList.toggle("is-error", Boolean(isError));
    toast.classList.add("is-visible");

    window.setTimeout(() => {
        toast.classList.remove("is-visible");
    }, 2600);
}

function setLoading(button, spinner, label, loading, idleText, loadingText) {
    button.disabled = loading;
    button.setAttribute("aria-busy", String(loading));
    spinner.style.display = loading ? "inline-block" : "none";
    label.textContent = loading ? loadingText : idleText;
}

function clearError(errorNode) {
    errorNode.textContent = "";
    errorNode.classList.remove("is-visible");
}

function showError(errorNode, message) {
    errorNode.textContent = message;
    errorNode.classList.add("is-visible");
}

function extractFilename(contentDisposition, fallback) {
    if (!contentDisposition) {
        return fallback;
    }

    const utfMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utfMatch && utfMatch[1]) {
        return decodeURIComponent(utfMatch[1]);
    }

    const basicMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
    if (basicMatch && basicMatch[1]) {
        return basicMatch[1];
    }

    return fallback;
}

async function parseErrorResponse(response, fallbackMessage) {
    let message = fallbackMessage;

    try {
        const data = await response.json();
        if (data && data.error) {
            message = data.error;
        }
    } catch (jsonErr) {
        const text = await response.text();
        if (text) {
            message = text;
        }
    }

    return message;
}

function triggerBlobDownload(blob, filename) {
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
}

async function generatePdfToExcel() {
    if (submitPdfBtn.disabled) {
        return;
    }

    clearError(errorPdf);

    const formData = new FormData(formPdf);
    const nombre = (formData.get("nombre_archivo") || "archivo_gtu").toString().trim() || "archivo_gtu";
    const fallbackName = `${nombre.replace(/\.xlsx$/i, "")}.xlsx`;

    setLoading(submitPdfBtn, spinnerPdf, labelPdf, true, "Generar y descargar Excel", "Generando...");

    try {
        const response = await fetch("/", {
            method: "POST",
            body: formData,
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        });

        if (!response.ok) {
            throw new Error(await parseErrorResponse(response, "No se pudo generar el archivo Excel."));
        }

        const blob = await response.blob();
        const filename = extractFilename(response.headers.get("Content-Disposition"), fallbackName);

        triggerBlobDownload(blob, filename);
        pushHistory(filename);
        showToast("Excel generado correctamente", false);
        formPdf.reset();
    } catch (error) {
        showError(errorPdf, error.message || "Ocurrió un error inesperado.");
        showToast("Error al generar Excel", true);
    } finally {
        setLoading(submitPdfBtn, spinnerPdf, labelPdf, false, "Generar y descargar Excel", "Generando...");
    }
}

async function generateExcelToTxt() {
    if (submitSnigBtn.disabled) {
        return;
    }

    clearError(errorSnig);

    const formData = new FormData(formSnig);
    const nombre = (formData.get("nombre_txt") || "salida_snig").toString().trim() || "salida_snig";
    const fallbackName = `${nombre.replace(/\.txt$/i, "")}.txt`;

    setLoading(submitSnigBtn, spinnerSnig, labelSnig, true, "Generar y descargar TXT", "Generando...");

    try {
        const response = await fetch("/excel-a-txt", {
            method: "POST",
            body: formData,
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        });

        if (!response.ok) {
            throw new Error(await parseErrorResponse(response, "No se pudo generar el TXT SNIG."));
        }

        const blob = await response.blob();
        const filename = extractFilename(response.headers.get("Content-Disposition"), fallbackName);

        triggerBlobDownload(blob, filename);
        pushHistory(filename);
        showToast("TXT SNIG generado correctamente", false);
        formSnig.reset();
    } catch (error) {
        showError(errorSnig, error.message || "Ocurrió un error inesperado.");
        showToast("Error al generar TXT SNIG", true);
    } finally {
        setLoading(submitSnigBtn, spinnerSnig, labelSnig, false, "Generar y descargar TXT", "Generando...");
    }
}

submitPdfBtn.addEventListener("click", generatePdfToExcel);
formPdf.addEventListener("submit", (event) => {
    event.preventDefault();
    generatePdfToExcel();
});

submitSnigBtn.addEventListener("click", generateExcelToTxt);
formSnig.addEventListener("submit", (event) => {
    event.preventDefault();
    generateExcelToTxt();
});

renderHistory();

/* ─── Sidebar & Navigation ───────────────────────────── */

const sidebar = document.getElementById("sidebar");
const sidebarToggle = document.getElementById("sidebar-toggle");
const appBarTitle = document.getElementById("app-bar-title");

const sectionTitles = {
    home: "Bienvenido",
    conversor: "Conversores de Archivos",
    anexos: "Creador de Anexos",
    "cdc-snig": "CDC SNIG",
    "stock-snig": "Descarga de Stock SNIG",
};

function navigateTo(sectionId) {
    document.querySelectorAll(".section").forEach((s) => s.classList.remove("is-active"));
    document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));

    const section = document.getElementById("sec-" + sectionId);
    if (section) section.classList.add("is-active");

    const navItem = document.querySelector(`.nav-item[data-section="${sectionId}"]`);
    if (navItem) navItem.classList.add("active");

    if (appBarTitle) appBarTitle.textContent = sectionTitles[sectionId] || "";
}

sidebarToggle.addEventListener("click", () => {
    sidebar.classList.toggle("collapsed");
});

document.querySelectorAll(".nav-item[data-section]").forEach((item) => {
    item.addEventListener("click", () => {
        navigateTo(item.dataset.section);
    });
});
document.querySelectorAll("[data-goto]").forEach((btn) => {
    btn.addEventListener("click", () => {
        navigateTo(btn.dataset.goto);
    });
});

// ─── Lógica del Wizard de Anexos ───────────────────

let currentStep = 1;
const totalSteps = 5;

const wizardSteps = document.querySelectorAll(".wizard-step");
const wizardNavItems = document.querySelectorAll(".step-nav-item");
const btnPrev = document.getElementById("btn-prev");
const btnNext = document.getElementById("btn-next");

const selectCliente = document.getElementById("select-cliente");
const btnNuevoCliente = document.getElementById("btn-nuevo-cliente");
const btnEditarCliente = document.getElementById("btn-editar-cliente");
const btnCancelarCliente = document.getElementById("btn-cancelar-cliente");
const formClienteWrap = document.getElementById("form-cliente-wrap");
const formCliente = document.getElementById("form-cliente");
const formClienteTitle = document.getElementById("form-cliente-title");

const inputFechaAnexo = document.getElementById("fecha-anexo");
const btnGenerarAnexo = document.getElementById("btn-generar-anexo");

// Seteamos fecha hoy por defecto
inputFechaAnexo.value = new Date().toISOString().split("T")[0];

const MONTHS_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

function formatDateSpanish(dateStr, formatType = "long") {
    if (!dateStr) return "---";
    const [year, month, day] = dateStr.split("-");
    const monthIndex = parseInt(month, 10) - 1;
    const monthName = MONTHS_ES[monthIndex];

    if (formatType === "filename") {
        const shortMonth = monthName.substring(0, 3).toLowerCase();
        const paddedDay = day.padStart(2, "0");
        return `${paddedDay}${shortMonth}${year}`;
    }

    return `${parseInt(day, 10)} de ${monthName} del ${year}`;
}

function updateWizard() {
    wizardSteps.forEach((s, idx) => {
        s.classList.toggle("is-active", idx + 1 === currentStep);
    });
    wizardNavItems.forEach((n, idx) => {
        const stepNum = idx + 1;
        n.classList.toggle("is-active", stepNum === currentStep);
        n.classList.toggle("is-completed", stepNum < currentStep);
    });

    btnPrev.style.visibility = currentStep === 1 ? "hidden" : "visible";
    btnNext.textContent = currentStep === totalSteps ? "Descargar" : "Siguiente";
    
    // Si entramos al paso de Clientes (ahora Paso 2), cargamos la lista filtrada
    if (currentStep === 2) {
        const fideicomisoActivo = document.querySelector('input[name="fideicomiso"]:checked').value;
        cargarClientes(fideicomisoActivo);
    }

    // Si estamos en el último paso, actualizamos resumen
    if (currentStep === 5) {
        updateSummary();
    }
}

function updateSummary() {
    const fideicomiso = document.querySelector('input[name="fideicomiso"]:checked').value;
    const anexo = document.querySelector('input[name="tipo_anexo"]:checked').value;
    const clienteText = selectCliente.options[selectCliente.selectedIndex].text;
    const fecha = inputFechaAnexo.value;

    document.getElementById("sum-fideicomiso").textContent = fideicomiso;
    document.getElementById("sum-anexo").textContent = anexo;
    document.getElementById("sum-cliente").textContent = clienteText;
    document.getElementById("sum-fecha").textContent = formatDateSpanish(fecha);

    // Sugerencia de nombre de archivo
    const n_cli = clienteText.replace(/ /g, "_");
    const f_anexo = formatDateSpanish(fecha, "filename");
    const n_anexo = anexo.split(" ")[1] || "X";
    document.getElementById("input-filename").value = `Anexo${n_anexo}_${n_cli}_${f_anexo}`;
}

btnNext.addEventListener("click", () => {
    if (currentStep === 2 && !selectCliente.value) {
        showToast("Por favor, seleccioná un cliente para continuar.", true);
        return;
    }
    if (currentStep === 4 && !inputFechaAnexo.value) {
        showToast("Por favor, ingresá la fecha del anexo.", true);
        return;
    }

    if (currentStep < totalSteps) {
        currentStep++;
        updateWizard();
    }
});

btnPrev.addEventListener("click", () => {
    if (currentStep > 1) {
        currentStep--;
        updateWizard();
    }
});

// --- Gestión de Clientes ---

async function cargarClientes(fideicomiso = null) {
    try {
        let url = "/anexos/clientes";
        if (fideicomiso) {
            url += `?fideicomiso=${encodeURIComponent(fideicomiso)}`;
        }
        
        const res = await fetch(url);
        const clientes = await res.json();
        
        const currentValue = selectCliente.value;
        selectCliente.innerHTML = '<option value="">-- Seleccionar Cliente --</option>';
        clientes.forEach(c => {
            const opt = document.createElement("option");
            opt.value = c.id;
            opt.textContent = c.razon_social;
            opt.dataset.raw = JSON.stringify(c);
            selectCliente.appendChild(opt);
        });
        
        if (currentValue) selectCliente.value = currentValue;
    } catch (err) {
        showToast("Error al cargar lista de clientes", true);
    }
}

selectCliente.addEventListener("change", () => {
    btnEditarCliente.disabled = !selectCliente.value;
});

btnNuevoCliente.addEventListener("click", () => {
    formCliente.reset();
    document.getElementById("cliente-id").value = "";
    formClienteTitle.textContent = "Cargar Nuevo Cliente";
    formClienteWrap.classList.add("is-visible");
});

btnEditarCliente.addEventListener("click", () => {
    const opt = selectCliente.selectedOptions[0];
    if (!opt || !opt.dataset.raw) return;
    
    const c = JSON.parse(opt.dataset.raw);
    document.getElementById("cliente-id").value = c.id;
    document.getElementById("cli-razon").value = c.razon_social;
    document.getElementById("cli-domicilio").value = c.domicilio_constituido;
    document.getElementById("cli-nombre").value = c.nombre_cliente || "";
    document.getElementById("cli-ci").value = c.ci || "";
    document.getElementById("cli-rut").value = c.rut || "";
    document.getElementById("cli-tel").value = c.telefono || "";
    document.getElementById("cli-mail").value = c.mail || "";

    formClienteTitle.textContent = "Editar Cliente";
    formClienteWrap.classList.add("is-visible");
});

btnCancelarCliente.addEventListener("click", () => {
    formClienteWrap.classList.remove("is-visible");
});

formCliente.addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("cliente-id").value;
    const method = id ? "PUT" : "POST";
    const url = id ? `/anexos/clientes/${id}` : "/anexos/clientes";
    
    const payload = {
        razon_social: document.getElementById("cli-razon").value,
        domicilio_constituido: document.getElementById("cli-domicilio").value,
        nombre_cliente: document.getElementById("cli-nombre").value,
        ci: document.getElementById("cli-ci").value,
        rut: document.getElementById("cli-rut").value,
        telefono: document.getElementById("cli-tel").value,
        mail: document.getElementById("cli-mail").value,
        fideicomiso: document.querySelector('input[name="fideicomiso"]:checked').value // ASOCIAR AL FIDEICOMISO ACTIVO
    };

    try {
        const res = await fetch(url, {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        
        if (result.ok) {
            showToast(id ? "Cliente actualizado" : "Cliente creado");
            formClienteWrap.classList.remove("is-visible");
            const fideicomisoActivo = document.querySelector('input[name="fideicomiso"]:checked').value;
            await cargarClientes(fideicomisoActivo);
            if (!id) selectCliente.value = result.cliente.id;
            btnEditarCliente.disabled = false;
        } else {
            showToast(result.error || "Error al guardar cliente", true);
        }
    } catch (err) {
        showToast("Error de conexión", true);
    }
});

// --- Generación de Anexo ---

const btnGenerarWord = document.getElementById("btn-generar-word");
const btnGenerarPdf = document.getElementById("btn-generar-pdf");

async function generarAnexo(formato) {
    const payload = {
        fideicomiso: document.querySelector('input[name="fideicomiso"]:checked').value,
        tipo_anexo: document.querySelector('input[name="tipo_anexo"]:checked').value,
        cliente_id: selectCliente.value,
        fecha: inputFechaAnexo.value,
        formato: formato,
        nombre_archivo: document.getElementById("input-filename").value
    };

    const targetBtn = formato === "pdf" ? btnGenerarPdf : btnGenerarWord;
    const spinner = targetBtn.querySelector(".spinner");
    const label = targetBtn.querySelector(".btn-label");
    const originalLabel = label.textContent;
    
    targetBtn.disabled = true;
    spinner.style.display = "inline-block";
    label.textContent = "Generando...";

    try {
        const res = await fetch("/anexos/generar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await res.json();

        if (result.ok) {
            window.location.href = `/anexos/descargar/${result.filename}`;
            showToast("Documento generado con éxito");
        } else {
            showToast(result.error || "Error al generar anexo", true);
        }
    } catch (err) {
        showToast("Error de red", true);
    } finally {
        targetBtn.disabled = false;
        spinner.style.display = "none";
        label.textContent = originalLabel;
    }
}

btnGenerarWord.addEventListener("click", () => generarAnexo("word"));
btnGenerarPdf.addEventListener("click", () => generarAnexo("pdf"));

// --- Previsualización ---

const previewModal = document.getElementById("preview-modal");
const btnPrevisualizar = document.getElementById("btn-previsualizar");
const btnClosePreview = document.getElementById("btn-close-preview");
const btnClosePreviewFooter = document.getElementById("btn-close-preview-footer");
const previewContainer = document.getElementById("document-preview-content");

function renderPreviewDoc() {
    const fideicomiso = document.querySelector('input[name="fideicomiso"]:checked').value;
    const anexo = document.querySelector('input[name="tipo_anexo"]:checked').value;
    const selectOpt = selectCliente.selectedOptions[0];
    const clienteData = selectOpt && selectOpt.dataset.raw ? JSON.parse(selectOpt.dataset.raw) : {};
    const fecha = inputFechaAnexo.value;

    previewContainer.innerHTML = `
        <div class="preview-doc-header">
            <h2 class="preview-doc-title">${fideicomiso.toUpperCase()}</h2>
            <p style="margin-top:10px; font-weight: bold;">DOCUMENTO DE ${anexo.toUpperCase()}</p>
        </div>
        <div class="preview-doc-body">
            <div class="preview-doc-section">
                <span class="preview-doc-label">Razón Social / Cliente:</span>
                <span class="preview-doc-value">${clienteData.razon_social || "---"}</span>
            </div>
            <div class="preview-doc-section">
                <span class="preview-doc-label">Domicilio Constituido:</span>
                <span class="preview-doc-value">${clienteData.domicilio_constituido || "---"}</span>
            </div>
            <div class="preview-doc-section">
                <span class="preview-doc-label">Fecha de Emisión:</span>
                <span class="preview-doc-value">${formatDateSpanish(fecha) || "---"}</span>
            </div>
            
            <div style="margin-top: 50px; line-height: 1.8; color: #475569; font-style: italic;">
                <p>Por la presente, el Sr./Sra. <strong>${clienteData.nombre_cliente || clienteData.razon_social}</strong> en su calidad de titular/apoderado, 
                manifiesta su voluntad de proceder con los términos establecidos en el <strong>${anexo}</strong>.</p>
                
                <p style="margin-top: 20px;">Este documento sirve como previsualización de los datos que serán consolidados en el archivo final (.docx o .pdf) 
                para su posterior firma y procesamiento legal dentro del marco del ${fideicomiso}.</p>
            </div>

            <div style="margin-top: 100px; display: flex; justify-content: space-between;">
                <div style="border-top: 1px solid #000; width: 200px; text-align: center; padding-top: 5px; font-size: 0.8rem;">
                    Firma del Cliente
                </div>
                <div style="border-top: 1px solid #000; width: 200px; text-align: center; padding-top: 5px; font-size: 0.8rem;">
                    Sello / Aclaración
                </div>
            </div>
        </div>
    `;
}

btnPrevisualizar.addEventListener("click", () => {
    renderPreviewDoc();
    previewModal.classList.add("is-visible");
});

const hidePreview = () => previewModal.classList.remove("is-visible");
btnClosePreview.addEventListener("click", hidePreview);
btnClosePreviewFooter.addEventListener("click", hidePreview);

// Cerrar modal al hacer clic fuera
previewModal.addEventListener("click", (e) => {
    if (e.target === previewModal) hidePreview();
});

// Inicialización extra cuando se navega a anexos
// Sobrescribimos o extendemos el navigateTo si es necesario, 
// o simplemente cargamos clientes al iniciar.
document.querySelector('.nav-item[data-section="anexos"]').addEventListener('click', cargarClientes);
cargarClientes(); // Carga inicial
