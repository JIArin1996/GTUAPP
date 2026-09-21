const STORAGE_KEY = "gtu_last_downloads_v1";
const MAX_ITEMS = 10;

const TIPO_COLORES = {
    pdf: "var(--blue-500)",
    snig: "var(--teal-500)",
    txt: "#a855f7",
    merge: "#f59e0b",
};

const blobCache = new Map();
let mergeFilesOrder = [];
let mergeDragSrcIndex = null;

const DB_NAME = "gtu_downloads_db";
const DB_STORE = "archivos";
const DB_VERSION = 1;

function abrirDb() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);
        request.onupgradeneeded = () => {
            request.result.createObjectStore(DB_STORE, { keyPath: "id" });
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

async function guardarArchivoDb(id, filename, blob) {
    try {
        const db = await abrirDb();
        await new Promise((resolve, reject) => {
            const tx = db.transaction(DB_STORE, "readwrite");
            tx.objectStore(DB_STORE).put({ id, filename, blob });
            tx.oncomplete = resolve;
            tx.onerror = () => reject(tx.error);
        });
        db.close();
    } catch (err) {
        // Almacenamiento no disponible (modo privado, cuota llena, etc.): la descarga ya se hizo, solo se pierde el re-descargar tras recargar.
    }
}

async function leerArchivoDb(id) {
    try {
        const db = await abrirDb();
        const registro = await new Promise((resolve, reject) => {
            const tx = db.transaction(DB_STORE, "readonly");
            const req = tx.objectStore(DB_STORE).get(id);
            req.onsuccess = () => resolve(req.result || null);
            req.onerror = () => reject(req.error);
        });
        db.close();
        return registro;
    } catch (err) {
        return null;
    }
}

async function eliminarArchivosDb(ids) {
    if (!ids.length) {
        return;
    }
    try {
        const db = await abrirDb();
        await new Promise((resolve, reject) => {
            const tx = db.transaction(DB_STORE, "readwrite");
            const store = tx.objectStore(DB_STORE);
            ids.forEach((id) => store.delete(id));
            tx.oncomplete = resolve;
            tx.onerror = () => reject(tx.error);
        });
        db.close();
    } catch (err) {
        // Ignorar: la limpieza es best-effort.
    }
}

const formPdf = document.getElementById("generador-form");
const submitPdfBtn = document.getElementById("submit-btn");
const spinnerPdf = submitPdfBtn.querySelector(".spinner");
const labelPdf = submitPdfBtn.querySelector(".btn-label");
const errorPdf = document.getElementById("error-message");
const campoNombreArchivo = document.getElementById("field-nombre-archivo");
const nombreArchivoInput = document.getElementById("nombre_archivo");
const archivoPdfInput = document.getElementById("archivo_pdf");
const pdfModoIndividualCheckbox = document.getElementById("pdf_modo_individual");
const pdfFileOrderWrap = document.getElementById("pdf-file-order");
const pdfFileList = document.getElementById("pdf-file-list");

let pdfFilesOrder = [];

const formSnig = document.getElementById("snig-form");
const submitSnigBtn = document.getElementById("snig-submit-btn");
const spinnerSnig = document.getElementById("snig-spinner");
const labelSnig = document.getElementById("snig-btn-label");
const errorSnig = document.getElementById("snig-error-message");
const campoArchivoExcel = document.getElementById("field-archivo-excel");
const archivoExcelInput = document.getElementById("archivo_excel");
const snigModoManualCheckbox = document.getElementById("snig_modo_manual");
const campoCaravanasManuales = document.getElementById("field-caravanas-manuales");
const caravanasManualesInput = document.getElementById("caravanas_manuales");

const SNIG_PATTERN = /(?<!\d)(8580000\d{8})(?!\d)/g;
const TXT_PREFIX = "A0000000";
const TXT_SUFFIX = "|.|.|.|.|.|.|.|.|.|.|]";

function extraerCaravanasDeTexto(texto) {
    const vistas = new Set();
    const caravanas = [];
    for (const match of texto.matchAll(SNIG_PATTERN)) {
        const caravana = match[1];
        if (!vistas.has(caravana)) {
            vistas.add(caravana);
            caravanas.push(caravana);
        }
    }
    return caravanas;
}

function construirTxtSnig(caravanas, guia) {
    const ahora = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const fecha = `${pad(ahora.getDate())}${pad(ahora.getMonth() + 1)}${ahora.getFullYear()}`;
    const hora = `${pad(ahora.getHours())}${pad(ahora.getMinutes())}`;

    return (
        caravanas.map((caravana) => `[|${TXT_PREFIX}${caravana}|${fecha}|${hora}|${guia}${TXT_SUFFIX}`).join("\n") + "\n"
    );
}

function updateSnigModoUI() {
    const modoManual = snigModoManualCheckbox.checked;
    campoArchivoExcel.classList.toggle("is-hidden", modoManual);
    campoCaravanasManuales.classList.toggle("is-hidden", !modoManual);
    archivoExcelInput.required = !modoManual;
    caravanasManualesInput.required = modoManual;
    clearError(errorSnig);
}

snigModoManualCheckbox.addEventListener("change", updateSnigModoUI);
updateSnigModoUI();

const formTxt = document.getElementById("txt-form");
const submitTxtBtn = document.getElementById("txt-submit-btn");
const spinnerTxt = document.getElementById("txt-spinner");
const labelTxt = document.getElementById("txt-btn-label");
const errorTxt = document.getElementById("txt-error-message");

const formMerge = document.getElementById("merge-form");
const submitMergeBtn = document.getElementById("merge-submit-btn");
const spinnerMerge = document.getElementById("merge-spinner");
const labelMerge = document.getElementById("merge-btn-label");
const errorMerge = document.getElementById("merge-error-message");
const formatoMergeSelect = document.getElementById("formato_merge");
const archivoMergeInput = document.getElementById("archivo_merge");
const archivoMergeLabel = document.getElementById("archivo-merge-label");
const nombreMergeInput = document.getElementById("nombre_merge");
const hojaMergeSelect = document.getElementById("hoja_merge");
const agregarOrigenMergeCheckbox = document.getElementById("agregar_origen_merge");
const hojaMergeField = document.getElementById("hoja-merge-field");
const origenMergeField = document.getElementById("origen-merge-field");
const mergeBadge = document.getElementById("merge-badge");
const mergeFileOrderWrap = document.getElementById("merge-file-order");
const mergeFileList = document.getElementById("merge-file-list");

const MERGE_FORMATS = {
    excel: {
        accept: ".xlsx,.xls,.csv",
        label: "Archivos Excel",
        badge: "XLS + XLS",
        buttonLabel: "Unir y descargar Excel",
        showExcelOptions: true,
    },
    txt: {
        accept: ".txt,text/plain",
        label: "Archivos TXT",
        badge: "TXT + TXT",
        buttonLabel: "Unir y descargar TXT",
        showExcelOptions: false,
    },
    pdf: {
        accept: ".pdf,application/pdf",
        label: "Archivos PDF",
        badge: "PDF + PDF",
        buttonLabel: "Unir y descargar PDF",
        showExcelOptions: false,
    },
    imagenes: {
        accept: ".png,.jpg,.jpeg,.webp,.bmp,image/*",
        label: "Imágenes",
        badge: "IMG + PDF",
        buttonLabel: "Unir y descargar PDF",
        showExcelOptions: false,
    },
};

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
            const color = TIPO_COLORES[item.tipo] || "var(--line)";
            return `<tr><td style="border-left:4px solid ${color}; padding-left:10px;"><button type="button" class="history-filename" data-history-id="${item.id || ""}">${item.filename}</button></td><td>${fecha}</td></tr>`;
        })
        .join("");
}

function pushHistory(filename, tipo, blob) {
    const id = `h_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    if (blob) {
        blobCache.set(id, { blob, filename });
        guardarArchivoDb(id, filename, blob);
    }

    const anteriores = loadHistory();
    const next = [{ id, filename, timestamp: new Date().toISOString(), tipo }, ...anteriores].slice(0, MAX_ITEMS);
    saveHistory(next);

    const idsDescartados = anteriores.slice(MAX_ITEMS - 1).map((item) => item.id).filter(Boolean);
    eliminarArchivosDb(idsDescartados);

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

historyBody.addEventListener("click", async (event) => {
    const btn = event.target.closest("[data-history-id]");
    if (!btn || !btn.dataset.historyId) {
        return;
    }

    const id = btn.dataset.historyId;
    let cached = blobCache.get(id);

    if (!cached) {
        const registro = await leerArchivoDb(id);
        if (registro) {
            cached = { blob: registro.blob, filename: registro.filename };
            blobCache.set(id, cached);
        }
    }

    if (!cached) {
        showToast("Ese archivo ya no está disponible para volver a descargar. Generalo de nuevo.", true);
        return;
    }

    triggerBlobDownload(cached.blob, cached.filename);
    showToast("Descarga iniciada", false);
});

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

function nombreSinExtension(filename) {
    return filename.replace(/\.pdf$/i, "");
}

function renderPdfFileOrder() {
    if (!pdfModoIndividualCheckbox.checked || pdfFilesOrder.length === 0) {
        pdfFileList.innerHTML = "";
        pdfFileOrderWrap.classList.remove("is-visible");
        return;
    }

    pdfFileOrderWrap.classList.add("is-visible");
    pdfFileList.innerHTML = pdfFilesOrder
        .map(
            (item, index) => `
                <li class="pdf-file-row" data-index="${index}">
                    <span class="merge-file-index">${index + 1}</span>
                    <input type="text" class="pdf-file-name-input" data-index="${index}" value="${item.nombre}">
                    <button type="button" class="pdf-file-remove" data-index="${index}" title="Quitar de la lista" aria-label="Quitar de la lista">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                </li>
            `
        )
        .join("");
}

function syncPdfFilesFromInput() {
    pdfFilesOrder = [...archivoPdfInput.files].map((file) => ({
        file,
        nombre: nombreSinExtension(file.name),
    }));
    renderPdfFileOrder();
}

function updatePdfModoUI() {
    const modoIndividual = pdfModoIndividualCheckbox.checked;
    campoNombreArchivo.classList.toggle("is-hidden", modoIndividual);
    nombreArchivoInput.required = !modoIndividual;

    if (modoIndividual) {
        syncPdfFilesFromInput();
    } else {
        pdfFilesOrder = [];
        renderPdfFileOrder();
    }
}

pdfModoIndividualCheckbox.addEventListener("change", updatePdfModoUI);

archivoPdfInput.addEventListener("change", () => {
    if (pdfModoIndividualCheckbox.checked) {
        syncPdfFilesFromInput();
    }
});

pdfFileList.addEventListener("input", (event) => {
    const input = event.target.closest(".pdf-file-name-input");
    if (!input) {
        return;
    }
    const index = Number(input.dataset.index);
    if (pdfFilesOrder[index]) {
        pdfFilesOrder[index].nombre = input.value;
    }
});

pdfFileList.addEventListener("click", (event) => {
    const btn = event.target.closest(".pdf-file-remove");
    if (!btn) {
        return;
    }
    const index = Number(btn.dataset.index);
    pdfFilesOrder.splice(index, 1);
    renderPdfFileOrder();
});

async function generarExcelDesdePdf(archivoPdf, nombreArchivo) {
    const formData = new FormData();
    formData.append("archivo_pdf", archivoPdf);
    formData.append("nombre_archivo", nombreArchivo);

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
    const fallbackName = `${nombreArchivo.replace(/\.xlsx$/i, "")}.xlsx`;
    const filename = extractFilename(response.headers.get("Content-Disposition"), fallbackName);

    triggerBlobDownload(blob, filename);
    pushHistory(filename, "pdf", blob);
}

async function generatePdfToExcelIndividual() {
    if (!pdfFilesOrder.length) {
        showError(errorPdf, "Debes cargar al menos un archivo PDF.");
        return;
    }

    setLoading(submitPdfBtn, spinnerPdf, labelPdf, true, "Generar y descargar Excel", "Generando...");

    let generados = 0;
    let primerError = null;

    for (const item of pdfFilesOrder) {
        const nombre = item.nombre.trim() || nombreSinExtension(item.file.name);
        try {
            await generarExcelDesdePdf(item.file, nombre);
            generados += 1;
        } catch (error) {
            primerError = primerError || error;
        }
    }

    setLoading(submitPdfBtn, spinnerPdf, labelPdf, false, "Generar y descargar Excel", "Generando...");

    if (generados > 0) {
        showToast(`${generados} de ${pdfFilesOrder.length} Excel generados`, Boolean(primerError));
    }

    if (primerError) {
        showError(errorPdf, primerError.message || "Ocurrió un error al generar alguno de los Excel.");
    } else {
        formPdf.reset();
        pdfFilesOrder = [];
        renderPdfFileOrder();
        updatePdfModoUI();
    }
}

async function generatePdfToExcel() {
    if (submitPdfBtn.disabled) {
        return;
    }

    clearError(errorPdf);

    if (pdfModoIndividualCheckbox.checked) {
        await generatePdfToExcelIndividual();
        return;
    }

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
        pushHistory(filename, "pdf", blob);
        showToast("Excel generado correctamente", false);
        formPdf.reset();
    } catch (error) {
        showError(errorPdf, error.message || "Ocurrió un error inesperado.");
        showToast("Error al generar Excel", true);
    } finally {
        setLoading(submitPdfBtn, spinnerPdf, labelPdf, false, "Generar y descargar Excel", "Generando...");
    }
}

async function generateExcelToTxtManual() {
    const guia = document.getElementById("guia").value.trim();
    if (!guia) {
        showError(errorSnig, "Debes ingresar el número de guía.");
        return;
    }
    if (!/^[A-Za-z]\d{6}$/.test(guia)) {
        showError(errorSnig, "El número de guía debe tener 1 letra seguida de 6 números (ej: D674195).");
        return;
    }

    const caravanas = extraerCaravanasDeTexto(caravanasManualesInput.value);
    if (!caravanas.length) {
        showError(errorSnig, "No se encontraron caravanas SNIG válidas (15 dígitos que comiencen con 8580000).");
        return;
    }

    const nombre = (document.getElementById("nombre_txt").value || "salida_snig").trim() || "salida_snig";
    const filename = `${nombre.replace(/\.txt$/i, "")}.txt`;

    setLoading(submitSnigBtn, spinnerSnig, labelSnig, true, "Generar y descargar TXT", "Generando...");

    try {
        const contenido = construirTxtSnig(caravanas, guia);
        const blob = new Blob([contenido], { type: "text/plain;charset=utf-8" });

        triggerBlobDownload(blob, filename);
        pushHistory(filename, "snig", blob);
        showToast("TXT SNIG generado correctamente", false);
        formSnig.reset();
        updateSnigModoUI();
    } finally {
        setLoading(submitSnigBtn, spinnerSnig, labelSnig, false, "Generar y descargar TXT", "Generando...");
    }
}

async function generateExcelToTxt() {
    if (submitSnigBtn.disabled) {
        return;
    }

    clearError(errorSnig);

    if (snigModoManualCheckbox.checked) {
        await generateExcelToTxtManual();
        return;
    }

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
        pushHistory(filename, "snig", blob);
        showToast("TXT SNIG generado correctamente", false);
        formSnig.reset();
    } catch (error) {
        showError(errorSnig, error.message || "Ocurrió un error inesperado.");
        showToast("Error al generar TXT SNIG", true);
    } finally {
        setLoading(submitSnigBtn, spinnerSnig, labelSnig, false, "Generar y descargar TXT", "Generando...");
    }
}

async function generateTxtToExcel() {
    if (submitTxtBtn.disabled) {
        return;
    }

    clearError(errorTxt);

    const formData = new FormData(formTxt);
    const nombre = (formData.get("nombre_excel") || "caravanas_extraidas").toString().trim() || "caravanas_extraidas";
    const fallbackName = `${nombre.replace(/\.xlsx$/i, "")}.xlsx`;

    setLoading(submitTxtBtn, spinnerTxt, labelTxt, true, "Generar y descargar Excel", "Generando...");

    try {
        const response = await fetch("/txt-a-excel", {
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
        pushHistory(filename, "txt", blob);
        showToast("Excel de TXT generado correctamente", false);
        formTxt.reset();
    } catch (error) {
        showError(errorTxt, error.message || "Ocurrió un error inesperado.");
        showToast("Error al generar Excel", true);
    } finally {
        setLoading(submitTxtBtn, spinnerTxt, labelTxt, false, "Generar y descargar Excel", "Generando...");
    }
}

function updateMergeFormatUI() {
    const config = MERGE_FORMATS[formatoMergeSelect.value];

    archivoMergeInput.accept = config.accept;
    archivoMergeInput.value = "";
    archivoMergeLabel.textContent = config.label;
    mergeBadge.textContent = config.badge;
    labelMerge.textContent = config.buttonLabel;

    hojaMergeField.classList.toggle("is-hidden", !config.showExcelOptions);
    origenMergeField.classList.toggle("is-hidden", !config.showExcelOptions);

    mergeFilesOrder = [];
    renderMergeFileOrder();

    clearError(errorMerge);
}

function renderMergeFileOrder() {
    if (mergeFilesOrder.length < 2) {
        mergeFileList.innerHTML = "";
        mergeFileOrderWrap.classList.remove("is-visible");
        return;
    }

    mergeFileOrderWrap.classList.add("is-visible");
    mergeFileList.innerHTML = mergeFilesOrder
        .map(
            (archivo, index) => `
                <li class="merge-file-row" draggable="true" data-index="${index}">
                    <span class="merge-file-grip" aria-hidden="true">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><circle cx="8" cy="6" r="1.6"/><circle cx="16" cy="6" r="1.6"/><circle cx="8" cy="12" r="1.6"/><circle cx="16" cy="12" r="1.6"/><circle cx="8" cy="18" r="1.6"/><circle cx="16" cy="18" r="1.6"/></svg>
                    </span>
                    <span class="merge-file-index">${index + 1}</span>
                    <span class="merge-file-name">${archivo.name}</span>
                </li>
            `
        )
        .join("");
}

async function mergeExcel(archivos, nombre, sheetMode, agregarOrigen) {
    const allRows = [];
    let globalHeader = null;

    for (const archivo of archivos) {
        const buffer = await archivo.arrayBuffer();
        let libro;
        try {
            libro = XLSX.read(buffer, { type: "array", cellDates: true });
        } catch (err) {
            continue;
        }

        const hojas = sheetMode === "all" ? libro.SheetNames : [libro.SheetNames[0]];

        for (const nombreHoja of hojas) {
            const hoja = libro.Sheets[nombreHoja];
            if (!hoja) {
                continue;
            }

            const datos = XLSX.utils.sheet_to_json(hoja, { header: 1, defval: "" });
            if (!datos.length) {
                continue;
            }

            const encabezado = datos[0];
            const filas = datos
                .slice(1)
                .filter((fila) => fila.some((celda) => celda !== "" && celda !== null && celda !== undefined));

            if (!globalHeader) {
                globalHeader = agregarOrigen ? ["Archivo origen", ...encabezado] : [...encabezado];
                allRows.push(globalHeader);
            }

            const nombreOrigen = hojas.length > 1 ? `${archivo.name} [${nombreHoja}]` : archivo.name;

            filas.forEach((fila) => {
                const filaCompleta = [...fila];
                while (filaCompleta.length < encabezado.length) {
                    filaCompleta.push("");
                }
                allRows.push(agregarOrigen ? [nombreOrigen, ...filaCompleta] : filaCompleta);
            });
        }
    }

    if (!globalHeader || allRows.length <= 1) {
        throw new Error("No se encontraron datos para unir en los archivos cargados.");
    }

    const libroNuevo = XLSX.utils.book_new();
    const hojaNueva = XLSX.utils.aoa_to_sheet(allRows);
    XLSX.utils.book_append_sheet(libroNuevo, hojaNueva, "Unido");

    const filename = `${nombre.replace(/\.xlsx$/i, "")}.xlsx`;
    const wbout = XLSX.write(libroNuevo, { bookType: "xlsx", type: "array" });
    const blob = new Blob([wbout], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });

    triggerBlobDownload(blob, filename);
    pushHistory(filename, "merge", blob);
}

async function mergeTxt(archivos, nombre) {
    const partes = [];
    for (const archivo of archivos) {
        const texto = await archivo.text();
        partes.push(texto.replace(/\s+$/, ""));
    }

    const contenido = `${partes.join("\n")}\n`;
    const blob = new Blob([contenido], { type: "text/plain;charset=utf-8" });
    const filename = `${nombre.replace(/\.txt$/i, "")}.txt`;

    triggerBlobDownload(blob, filename);
    pushHistory(filename, "merge", blob);
}

async function mergeEnServidor(url, campoArchivos, campoNombre, archivos, nombre, fallbackName) {
    const formData = new FormData();
    archivos.forEach((archivo) => formData.append(campoArchivos, archivo));
    formData.append(campoNombre, nombre);

    const response = await fetch(url, {
        method: "POST",
        body: formData,
        headers: {
            "X-Requested-With": "XMLHttpRequest",
        },
    });

    if (!response.ok) {
        throw new Error(await parseErrorResponse(response, "No se pudieron unir los archivos."));
    }

    const blob = await response.blob();
    const filename = extractFilename(response.headers.get("Content-Disposition"), fallbackName);

    triggerBlobDownload(blob, filename);
    pushHistory(filename, "merge", blob);
}

async function generateMerge() {
    if (submitMergeBtn.disabled) {
        return;
    }

    clearError(errorMerge);

    const formato = formatoMergeSelect.value;
    const config = MERGE_FORMATS[formato];
    const archivos = mergeFilesOrder.length ? mergeFilesOrder : [...archivoMergeInput.files];
    const nombre = nombreMergeInput.value.trim() || "unido";

    if (!archivos.length) {
        showError(errorMerge, "Debes cargar al menos un archivo.");
        return;
    }

    setLoading(submitMergeBtn, spinnerMerge, labelMerge, true, config.buttonLabel, "Uniendo...");

    try {
        if (formato === "excel") {
            await mergeExcel(archivos, nombre, hojaMergeSelect.value, agregarOrigenMergeCheckbox.checked);
        } else if (formato === "txt") {
            await mergeTxt(archivos, nombre);
        } else if (formato === "pdf") {
            await mergeEnServidor("/unir-pdf", "archivo_pdf_merge", "nombre_pdf_merge", archivos, nombre, `${nombre}.pdf`);
        } else if (formato === "imagenes") {
            await mergeEnServidor("/unir-imagenes", "archivo_imagen_merge", "nombre_imagen_merge", archivos, nombre, `${nombre}.pdf`);
        }

        showToast("Archivos unidos correctamente", false);
        formMerge.reset();
        updateMergeFormatUI();
    } catch (error) {
        showError(errorMerge, error.message || "Ocurrió un error inesperado.");
        showToast("Error al unir los archivos", true);
    } finally {
        setLoading(submitMergeBtn, spinnerMerge, labelMerge, false, config.buttonLabel, "Uniendo...");
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

submitTxtBtn.addEventListener("click", generateTxtToExcel);
formTxt.addEventListener("submit", (event) => {
    event.preventDefault();
    generateTxtToExcel();
});

formatoMergeSelect.addEventListener("change", updateMergeFormatUI);

archivoMergeInput.addEventListener("change", () => {
    mergeFilesOrder = [...archivoMergeInput.files];
    renderMergeFileOrder();
});

mergeFileList.addEventListener("dragstart", (event) => {
    const row = event.target.closest(".merge-file-row");
    if (!row) {
        return;
    }
    mergeDragSrcIndex = Number(row.dataset.index);
    row.classList.add("is-dragging");
    event.dataTransfer.effectAllowed = "move";
});

mergeFileList.addEventListener("dragend", (event) => {
    const row = event.target.closest(".merge-file-row");
    if (row) {
        row.classList.remove("is-dragging");
    }
    mergeDragSrcIndex = null;
});

mergeFileList.addEventListener("dragover", (event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
});

mergeFileList.addEventListener("drop", (event) => {
    event.preventDefault();
    const row = event.target.closest(".merge-file-row");
    if (!row || mergeDragSrcIndex === null) {
        return;
    }

    const targetIndex = Number(row.dataset.index);
    if (targetIndex === mergeDragSrcIndex) {
        return;
    }

    const [moved] = mergeFilesOrder.splice(mergeDragSrcIndex, 1);
    mergeFilesOrder.splice(targetIndex, 0, moved);
    mergeDragSrcIndex = null;
    renderMergeFileOrder();
});

submitMergeBtn.addEventListener("click", generateMerge);
formMerge.addEventListener("submit", (event) => {
    event.preventDefault();
    generateMerge();
});

updateMergeFormatUI();
renderHistory();
