const API_BASE = "http://127.0.0.1:8000/documents";

// --- Upload PDF (single or multiple) ---
document.getElementById("upload-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = document.getElementById("file-input");
    if (!input.files.length) return alert("Select PDF file(s)");

    const formData = new FormData();
    for (const file of input.files) {
        formData.append("files", file);
    }

    try {
        const res = await fetch(`${API_BASE}/upload-multiple`, { method: "POST", body: formData });
        const data = await res.json();
        alert(`Uploaded: ${data.uploaded.map(f => f.filename).join(", ")}`);
        input.value = ""; // Clear file input
        loadDocuments();
    } catch (err) {
        console.error(err);
        alert("Upload failed");
    }
});

// --- Load documents ---
async function loadDocuments() {
    const list = document.getElementById("documents-list");
    list.innerHTML = "";
    try {
        const res = await fetch(`${API_BASE}/`);
        const docs = await res.json();
        docs.forEach(doc => {
            const li = document.createElement("li");
            li.innerHTML = `
                <strong>${doc.filename}</strong>
                <button onclick="viewPDF('${doc.filename}')">View</button>
                <button onclick="downloadPDF('${doc.filename}')">Download</button>
                <button onclick="deletePDF('${doc.filename}')">Delete</button>
                <div>Preview: ${doc.preview}</div>
                <div>AI Summary: ${doc.summary}</div>
            `;
            list.appendChild(li);
        });
    } catch (err) {
        console.error(err);
    }
}
loadDocuments();

// --- View PDF ---
function viewPDF(filename) {
    const iframe = document.getElementById("pdf-preview");
    iframe.src = `${API_BASE}/view/${encodeURIComponent(filename)}`;
}

// --- Download PDF ---
function downloadPDF(filename) {
    window.open(`${API_BASE}/download/${encodeURIComponent(filename)}`, "_blank");
}

// --- Delete PDF ---
async function deletePDF(filename) {
    if (!confirm(`Delete ${filename}?`)) return;
    try {
        await fetch(`${API_BASE}/file/${encodeURIComponent(filename)}`, { method: "DELETE" });
        document.getElementById("pdf-preview").src = ""; // Clear preview
        loadDocuments();
        // Also remove from search results if exists
        const results = document.getElementById("search-results").children;
        for (let li of results) {
            if (li.querySelector(".filename")?.textContent === filename) {
                li.remove();
            }
        }
    } catch (err) {
        console.error(err);
        alert("Delete failed");
    }
}

// --- Refresh button ---
document.getElementById("refresh-btn").addEventListener("click", loadDocuments);

// --- Search ---
document.getElementById("search-btn").addEventListener("click", async () => {
    const query = document.getElementById("search-query").value.trim();
    const searchResults = document.getElementById("search-results");

    if (!query) return alert("Enter search keyword");

    try {
        const res = await fetch(`${API_BASE}/search?query=${encodeURIComponent(query)}`);
        if (!res.ok) throw new Error("Search request failed");

        const results = await res.json();

        // Smoothly replace previous results
        Array.from(searchResults.children).forEach(child => searchResults.removeChild(child));

        if (results.length === 0) {
            const li = document.createElement("li");
            li.textContent = "No results found.";
            searchResults.appendChild(li);
            return;
        }

        results.forEach(r => {
            const li = document.createElement("li");
            li.className = "search-result";
            li.innerHTML = `
                <h3 class="filename">${r.filename}</h3>
                <p class="summary">🧠 AI Summary: ${r.summary || "No summary available"}</p>
                <p class="preview">🔍 Preview: ${r.preview || "No preview text"}</p>
                <button onclick="viewPDF('${r.filename}')">👁️ View</button>
                <button onclick="downloadPDF('${r.filename}')">⬇️ Download</button>
            `;
            searchResults.appendChild(li);
        });

        // Scroll to results smoothly
        searchResults.scrollIntoView({ behavior: "smooth" });

    } catch (err) {
        console.error(err);
        searchResults.innerHTML = "<li>❌ Error searching files. Check console.</li>";
    }
});

// --- Clear Elasticsearch Index ---
document.getElementById("clear-index-btn").addEventListener("click", async () => {
    if (!confirm("Are you sure you want to clear the entire Elasticsearch index?")) return;
    try {
        const res = await fetch(`${API_BASE}/clear-index`, { method: "DELETE" });
        const data = await res.json();
        alert(data.message);
    } catch (err) {
        console.error(err);
        alert("Failed to clear index");
    }
});

// --- Reindex All PDFs ---
document.getElementById("reindex-btn").addEventListener("click", async () => {
    if (!confirm("Reindex all PDFs in Elasticsearch?")) return;
    try {
        const res = await fetch(`${API_BASE}/reindex-all`, { method: "POST" });
        const data = await res.json();
        alert(data.message);
    } catch (err) {
        console.error(err);
        alert("Reindex failed");
    }
});