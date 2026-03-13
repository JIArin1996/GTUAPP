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
