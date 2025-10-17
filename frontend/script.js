const API_BASE = "http://127.0.0.1:8000/documents";

// ============ Upload single/multi ============
document.getElementById("upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("file-input");
  if (!input.files.length) return alert("Select PDF file(s)");

  // prefer /upload-multiple – akceptuje multi
  const form = new FormData();
  for (const f of input.files) form.append("files", f);

  const res = await fetch(`${API_BASE}/upload-multiple`, { method: "POST", body: form });
  if (!res.ok) {
    document.getElementById("upload-result").textContent = "❌ Upload failed. Check server logs.";
    return;
  }
  const data = await res.json();
  document.getElementById("upload-result").textContent = data.message || "✅ Uploaded";
  input.value = "";
  await loadDocuments();
  await refreshAdmin();
});

// ============ Document list ============
async function loadDocuments() {
  const list = document.getElementById("documents-list");
  list.innerHTML = "";
  const res = await fetch(`${API_BASE}/`);
  if (!res.ok) return;

  const docs = await res.json();
  docs.forEach(doc => {
    const li = document.createElement("li");
    li.innerHTML = `
      <strong>${doc.filename}</strong>
      <button onclick="viewPDF('${doc.filename}')">View</button>
      <button onclick="downloadPDF('${doc.filename}')">Download</button>
      <button onclick="deletePDF('${doc.filename}')">Delete</button>
    `;
    list.appendChild(li);
  });
}
loadDocuments();

document.getElementById("refresh-btn").addEventListener("click", loadDocuments);

// ============ View / Download / Delete ============
function viewPDF(filename) {
  const iframe = document.getElementById("pdf-preview");
  iframe.src = `${API_BASE}/view/${encodeURIComponent(filename)}`;
}
function downloadPDF(filename) {
  window.open(`${API_BASE}/download/${encodeURIComponent(filename)}`, "_blank");
}
async function deletePDF(filename) {
  if (!confirm(`Delete ${filename}?`)) return;
  await fetch(`${API_BASE}/file/${encodeURIComponent(filename)}`, { method: "DELETE" });
  document.getElementById("pdf-preview").src = "";
  await loadDocuments();
  await refreshAdmin();
}

// ============ Search ============
document.getElementById("search-btn").addEventListener("click", async () => {
  const q = document.getElementById("search-query").value.trim();
  const list = document.getElementById("search-results");
  list.innerHTML = "";
  if (!q) return;

  const res = await fetch(`${API_BASE}/search?query=${encodeURIComponent(q)}`);
  if (!res.ok) {
    list.innerHTML = "<li>❌ Error searching.</li>";
    return;
  }
  const results = await res.json();
  if (!results.length) {
    list.innerHTML = "<li>No results found.</li>";
    return;
  }
  results.forEach(r => {
    const li = document.createElement("li");
    li.className = "search-result";
    li.innerHTML = `
      <h3 class="filename">${r.filename}</h3>
      <p class="summary">🧠 AI Summary: ${r.summary || "No summary available"}</p>
      <p class="lang">🌍 Language: ${r.language || "unknown"}</p>
      <p class="preview">🔍 Preview: ${r.preview || "—"}</p>
      <button onclick="viewPDF('${r.filename}')">👁️ View</button>
      <button onclick="downloadPDF('${r.filename}')">⬇️ Download</button>
    `;
    list.appendChild(li);
  });
});

// ============ ES index mgmt ============
document.getElementById("clear-index-btn").addEventListener("click", async () => {
  if (!confirm("Clear entire Elasticsearch index?")) return;
  const res = await fetch(`${API_BASE}/clear-index`, { method: "DELETE" });
  const data = await res.json();
  alert(data.message || "Done");
  await refreshAdmin();
});

document.getElementById("reindex-btn").addEventListener("click", async () => {
  if (!confirm("Reindex all PDFs?")) return;
  const res = await fetch(`${API_BASE}/reindex-all`, { method: "POST" });
  const data = await res.json();
  alert(data.message || "Done");
  await refreshAdmin();
});

// ============ Admin Dashboard ============
async function refreshAdmin() {
  try {
    const res = await fetch(`${API_BASE}/admin/health`);
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById("app-status").textContent = data.app || "—";
    document.getElementById("es-status").textContent = data.elasticsearch?.connected ? "Connected" : "Down";
    document.getElementById("es-index").textContent = data.elasticsearch?.index || "—";
    document.getElementById("es-docs").textContent = data.elasticsearch?.docs ?? "—";
    document.getElementById("vertex-status").textContent = data.vertex_ai?.enabled ? "Enabled" : "Disabled";

    // SQLite count
    const statusRes = await fetch(`${API_BASE}/status`);
    if (statusRes.ok) {
      const st = await statusRes.json();
      document.getElementById("sqlite-docs").textContent = st.local_files ?? "—";
      const ul = document.getElementById("recent-files");
      ul.innerHTML = "";
      // optional: show just names
      const listRes = await fetch(`${API_BASE}/`);
      if (listRes.ok) {
        const files = await listRes.json();
        files.slice(0, 5).forEach(f => {
          const li = document.createElement("li");
          li.textContent = f.filename;
          ul.appendChild(li);
        });
      }
    }
  } catch (e) {
    console.error(e);
  }
}
document.getElementById("admin-refresh").addEventListener("click", refreshAdmin);
refreshAdmin();