const STORAGE_KEY = "gtu_last_downloads_v1";
const MAX_ITEMS = 5;

const form = document.getElementById("generador-form");
const submitBtn = document.getElementById("submit-btn");
const spinner = document.querySelector(".spinner");
const btnLabel = document.querySelector(".btn-label");
const errorMessage = document.getElementById("error-message");
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

function setLoading(loading) {
    submitBtn.disabled = loading;
    submitBtn.setAttribute("aria-busy", String(loading));
    spinner.style.display = loading ? "inline-block" : "none";
    btnLabel.textContent = loading ? "Generando..." : "Generar y descargar Excel";
}

function clearError() {
    errorMessage.textContent = "";
    errorMessage.classList.remove("is-visible");
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.add("is-visible");
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

async function generateAndDownload() {
    if (submitBtn.disabled) {
        return;
    }

    clearError();

    const formData = new FormData(form);
    const nombre = (formData.get("nombre_archivo") || "archivo_gtu").toString().trim() || "archivo_gtu";
    const fallbackName = `${nombre.replace(/\.xlsx$/i, "")}.xlsx`;

    setLoading(true);

    try {
        const response = await fetch("/", {
            method: "POST",
            body: formData,
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        });

        if (!response.ok) {
            let message = "No se pudo generar el archivo.";
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
            throw new Error(message);
        }

        const blob = await response.blob();
        const contentDisposition = response.headers.get("Content-Disposition");
        const filename = extractFilename(contentDisposition, fallbackName);

        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(objectUrl);

        pushHistory(filename);
        showToast("Archivo generado correctamente", false);
        form.reset();
    } catch (error) {
        showError(error.message || "Ocurrió un error inesperado.");
        showToast("Error al generar el archivo", true);
    } finally {
        setLoading(false);
    }
}

function onSubmit(event) {
    event.preventDefault();
    if (!submitBtn.disabled) {
        generateAndDownload();
    }
}

submitBtn.addEventListener("click", generateAndDownload);
form.addEventListener("submit", onSubmit);

form.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && event.target.tagName !== "TEXTAREA") {
        event.preventDefault();
        if (!submitBtn.disabled) {
            generateAndDownload();
        }
    }
});

renderHistory();
