// ==========================
// ✅ SMARTDOCFINDER FRONTEND
// ==========================

console.log("🚀 SmartDocFinder frontend loaded.");
const API_BASE = "https://smartdocfinder-861730700785.europe-west1.run.app";

// ==========================
// 📦 FUNCTION: handleUpload
// ==========================
async function handleUpload(e) {
  e?.preventDefault?.();
  const input = document.getElementById("file-input");
  const result = document.getElementById("upload-result");

  if (!input?.files?.length) {
    result.textContent = "⚠️ Select PDF file(s) first.";
    return;
  }

  const form = new FormData();
  for (const f of input.files) form.append("files", f);

  result.textContent = "⏳ Uploading...";
  try {
    const res = await fetch(`${API_BASE}/upload-multiple`, { method: "POST", body: form });

    if (!res.ok) throw new Error("Upload failed");
    const data = await res.json();

    let message = "";
    for (const f of data.uploaded || []) {
      if (f.status === "duplicate") {
        message += `
          ⚠️ <strong>${f.filename}</strong> already exists.<br>
          📂 Location: <span style="color:#38bdf8;font-weight:bold;">${f.folder}</span><br><br>
        `;
      } else {
        message += `✅ Uploaded <strong>${f.filename}</strong><br>`;
      }
    }

    result.innerHTML = message || "✅ Uploaded successfully.";
    await loadDocuments();
    await refreshAdmin();

  } catch (err) {
    console.error("Upload error:", err);
    result.textContent = "❌ Upload failed.";
  }
}

// ==========================
// 📄 FUNCTION: loadDocuments
// ==========================
async function loadDocuments() {
  const list = document.getElementById("documents-list");
  if (!list) return;

  list.innerHTML = "<li>⏳ Loading documents...</li>";

  try {
    const res = await fetch(`${API_BASE}/`);
    if (!res.ok) throw new Error(`Failed to load documents (HTTP ${res.status})`);
    const docs = await res.json();

    list.innerHTML = "";


    docs.forEach((doc) => {
      const li = document.createElement("li");
      li.innerHTML = `
        <div>
          <strong class="filename">${doc.filename}</strong>
          <div style="margin-top:6px;">
            <button onclick="viewPDF('${doc.filename}')">👁️ View</button>
            <button onclick="downloadPDF('${doc.filename}')">⬇️ Download</button>
            <button onclick="deletePDF('${doc.filename}')">🗑️ Delete</button>
            <select class="move-select" onchange="moveToFolder('${doc.filename}', this.value)">
              <option value="">📁 Move to...</option>
            </select>
          </div>
        </div>
      `;
      list.appendChild(li);
    });

    // Populate folder dropdowns dynamically
    await populateFolderDropdowns();
  } catch (err) {
    console.error("❌ Error loading documents:", err);
    list.innerHTML = "<li>❌ Failed to load documents.</li>";
  }
}

// ==========================
// 📁 FUNCTION: populateFolderDropdowns
// ==========================
async function populateFolderDropdowns() {
  try {
    const res = await fetch(`${API_BASE}/folders`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const folders = data.folders || [];

    document.querySelectorAll("select").forEach((sel) => {
      // tylko dropdowny "Move to..."
      if (sel.innerHTML.includes("Move to...")) {
        const options = ['<option value="">📁 Move to...</option>']
          .concat(folders.map((f) => `<option value="${f}">${f}</option>`));
        sel.innerHTML = options.join("");
      }
    });
  } catch (err) {
    console.error("⚠️ Folder dropdown load failed:", err);
  }
}
// ==========================
// 👁️ FUNCTION: viewPDF
// ==========================
function viewPDF(filename) {
  const iframe = document.getElementById("pdf-preview");
  if (!iframe) {
    console.warn("⚠️ Missing <iframe id='pdf-preview'> element in HTML.");
    return;
  }

  iframe.src = `${API_BASE}/view/${encodeURIComponent(filename)}`;
  iframe.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ==========================
// 📥 FUNCTION: downloadPDF
// ==========================
function downloadPDF(filename) {
  if (!filename) {
    console.warn("⚠️ No filename provided for download.");
    return;
  }
  window.open(`${API_BASE}/download/${encodeURIComponent(filename)}`, "_blank");
}
// ==========================
// 🗑️ FUNCTION: deletePDF (universal delete + auto-refresh folder view)
// ==========================
async function deletePDF(filename, folderName = null) {
  if (!filename) {
    console.warn("⚠️ No filename provided for deletion.");
    return;
  }

  if (!confirm(`Are you sure you want to delete "${filename}"?`)) return;

  try {
    console.log("🌐 DELETE:", `${API_BASE}/file/${encodeURIComponent(filename)}`);

    const res = await fetch(`${API_BASE}/file/${encodeURIComponent(filename)}`, {
      method: "DELETE",
    });

    const data = await res.json().catch(() => ({}));
    console.log("📡 Response:", res.status, data);

    if (!res.ok) {
      throw new Error(data?.detail || `HTTP ${res.status}`);
    }

    console.log(`✅ File "${filename}" deleted successfully.`);

    // 🧹 Clear PDF preview (if visible)
    const iframe = document.getElementById("pdf-preview");
    if (iframe && iframe.src.includes(filename)) iframe.src = "";

    // 🔁 Refresh global UI
    if (typeof loadDocuments === "function") await loadDocuments();
    if (typeof refreshAdmin === "function") await refreshAdmin();

    // 🔄 If user was inside a folder — reload its contents dynamically
    if (folderName) {
      const panelId = `panel_${folderName.replace(/[^a-zA-Z0-9_-]/g, "_")}`;
      const panel = document.getElementById(panelId);
      if (panel) {
        panel.remove(); // remove old panel
        await openFolder(folderName); // reopen refreshed panel
      }
    }

    alert(`✅ "${filename}" deleted successfully.`);
  } catch (err) {
    console.error("❌ Delete error:", err);
    alert("❌ Failed to delete file.");
  }
}
// ==========================
// 📂 FUNCTION: moveToFolder
// ==========================
async function moveToFolder(filename, folderName) {
  if (!filename || !folderName) {
    console.warn("⚠️ Missing filename or folder name.");
    return;
  }

  if (!confirm(`Move "${filename}" → "${folderName}"?`)) return;

  try {
    const res = await fetch(`${API_BASE}/move-to-folder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename, folder: folderName }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    alert(data.message || `✅ File moved to ${folderName}.`);

    await loadDocuments();
    await refreshAdmin();
  } catch (err) {
    console.error("❌ Move file error:", err);
    alert("❌ Failed to move file.");
  }
}
// ==========================
// 🔍 FUNCTION: searchDocuments
// ==========================
document.getElementById("search-btn").addEventListener("click", async () => {
  const btn = document.getElementById("search-btn");
  const q = document.getElementById("search-query").value.trim();
  const list = document.getElementById("search-results");
  list.innerHTML = "";

  if (!q) return;

  // 🔄 Start animation
  btn.disabled = true;
  btn.textContent = "Searching…";
  btn.classList.add("searching");

  try {
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
  } catch (err) {
    console.error("❌ Search error:", err);
    list.innerHTML = "<li>❌ Failed to fetch results.</li>";
  } finally {
    // ✅ Stop animation
    btn.disabled = false;
    btn.textContent = "Search";
    btn.classList.remove("searching");
  }
});

// ==========================
// ♻️ FUNCTION: refreshAdmin (dashboard bottom cards)
// ==========================
function setCardState(cardEl, ok) {
  if (!cardEl) return;
  cardEl.classList.remove("ok", "err");
  cardEl.classList.add(ok ? "ok" : "err");
}

async function refreshAdmin() {
  const errBox = document.getElementById("admin-error");

  try {
    const res = await fetch(`${API_BASE}/admin/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // ---- wartości liczbowe/teksty jak wcześniej ----
    document.getElementById("es-connected").textContent =
      data.elasticsearch?.connected ? "🟢 Connected" : "🔴 Down";
    document.getElementById("es-index").textContent =
      `index: ${data.elasticsearch?.index || "—"}`;
    document.getElementById("es-index-exists").textContent =
      `exists: ${data.elasticsearch?.connected ? "✅" : "❌"}`;
    document.getElementById("docs-count").textContent =
      data.elasticsearch?.docs ?? "—";
    document.getElementById("vertex-enabled").textContent =
      data.vertex_ai?.enabled ? "🧠 Enabled" : "⚪ Disabled";
    document.getElementById("vertex-model").textContent =
      `model: ${data.vertex_ai?.model || "—"}`;
    document.getElementById("admin-updated").textContent =
      new Date().toLocaleTimeString();

    // ---- kolorowe obramowanie kart (LEWY border) ----
    const esOK = !!data.elasticsearch?.connected;
    const vertexOK = !!data.vertex_ai?.enabled;

    // Jeśli chcesz, żeby „Documents” było zielone tylko gdy są jakiekolwiek dokumenty:
    const docsValRaw = data.elasticsearch?.docs;
    const docsNumber = typeof docsValRaw === "number" ? docsValRaw : parseInt(docsValRaw, 10);
    const docsOK = Number.isFinite(docsNumber) ? docsNumber > 0 : esOK; // fallback: jak ES żyje, traktuj OK

    setCardState(document.getElementById("card-es"), esOK);
    setCardState(document.getElementById("card-vertex"), vertexOK);
    setCardState(document.getElementById("card-docs"), docsOK);

    // karta „Last update” zostaje neutralna – bez .ok/.err
    // (jeśli chcesz też kolorować, odkomentuj poniżej)
    // setCardState(document.getElementById("card-updated"), esOK && vertexOK);

    // reset błędu
    if (errBox) {
      errBox.style.display = "none";
      errBox.textContent = "";
    }
  } catch (err) {
    console.error("Dashboard error:", err);
    if (errBox) {
      errBox.textContent = "Dashboard failed to load.";
      errBox.style.display = "block";
    }
    // w razie błędu zaznacz karty na czerwono
    setCardState(document.getElementById("card-es"), false);
    setCardState(document.getElementById("card-vertex"), false);
    setCardState(document.getElementById("card-docs"), false);
  }
}
// ==========================
// 📋 FUNCTION: ADMIN MENU (Dropdown)
// ==========================
const dropdown = document.getElementById("admin-dropdown");
const adminBtn = document.getElementById("admin-menu-btn");
const adminContent = document.getElementById("admin-content");

// 🔹 Kliknięcie przycisku Admin ▼
if (adminBtn) {
  adminBtn.addEventListener("click", () => {
    dropdown.style.display = dropdown.style.display === "none" ? "block" : "none";
  });
}

// 🔹 Zamknięcie menu po kliknięciu poza nim
document.addEventListener("click", (e) => {
  if (!adminBtn.contains(e.target) && !dropdown.contains(e.target)) {
    dropdown.style.display = "none";
  }
});
// ==========================
// 🧩 FUNCTION: showAdminTab(tab)
// ==========================
async function showAdminTab(tab) {
  const adminContent = document.getElementById("admin-content");
  adminContent.style.display = "block";
  adminContent.innerHTML = "⏳ Loading...";
  adminContent.scrollIntoView({ behavior: "smooth", block: "start" });

  try {
    // ==================
    // 🩺 SYSTEM STATUS
    // ==================
    if (tab === "status") {
      const res = await fetch(`${API_BASE}/admin/health`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const es = data.elasticsearch || {};
      const vertex = data.vertex_ai || {};

      adminContent.innerHTML = `
        <h3>🩺 System Status</h3>
        <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:12px;">
          <p><strong>📦 App:</strong> ${data.app || "unknown"}</p>
          <p><strong>🔍 Elasticsearch:</strong> ${es.connected ? "🟢 Connected" : "🔴 Down"}</p>
          <p><strong>📁 Index:</strong> ${es.index || "—"}</p>
          <p><strong>📄 Docs Count:</strong> ${es.docs ?? "—"}</p>
          <p><strong>🤖 Vertex AI:</strong> ${
            vertex.enabled ? `🧠 Enabled (${vertex.model || "—"})` : "⚪ Disabled"
          }</p>
        </div>

        <div style="margin-top:20px; display:flex; gap:10px; flex-wrap:wrap;">
          <button id="refresh-status-btn">🔄 Refresh Status</button>
          <button id="clear-index-btn">🧹 Clear Index</button>
          <button id="reindex-all-btn">🔁 Reindex All</button>
        </div>

        <div id="status-log" style="margin-top:15px;color:#94a3b8;font-size:0.95em;"></div>
      `;

      // 🔸 Eventy dla przycisków
      document.getElementById("refresh-status-btn")?.addEventListener("click", async () => {
        await showAdminTab("status");
      });

      document.getElementById("clear-index-btn")?.addEventListener("click", async () => {
        if (!confirm("Clear entire Elasticsearch index?")) return;
        const log = document.getElementById("status-log");
        log.textContent = "⏳ Clearing index...";
        const res = await fetch(`${API_BASE}/clear-index`, { method: "DELETE" });
        const data = await res.json();
        log.textContent = data.message || "✅ Index cleared.";
        await refreshAdmin();
      });

      document.getElementById("reindex-all-btn")?.addEventListener("click", async () => {
        if (!confirm("Rebuild Elasticsearch index?")) return;
        const log = document.getElementById("status-log");
        log.textContent = "⏳ Reindexing all documents...";
        const res = await fetch(`${API_BASE}/reindex-all`, { method: "POST" });
        const data = await res.json();
        log.textContent = data.message || "✅ Reindex complete.";
        await refreshAdmin();
      });
      return;
    }

    // ==================
    // 📁 FOLDERS
    // ==================
    if (tab === "folders") {
      const res = await fetch(`${API_BASE}/folders`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const folders = data.folders || [];

      const folderList = folders.length
        ? folders
            .map(
              (f) => `
                <div class="folder-item" style="margin:6px 0;">
                  📂 <span class="folder-name" data-folder="${f}" style="cursor:pointer;color:#38bdf8;font-weight:bold;">${f}</span>
                  <button class="delete-folder-btn" data-folder="${f}" style="margin-left:8px;color:#fff;background:#b91c1c;border:1px solid #7f1d1d;border-radius:6px;padding:2px 8px;">Delete</button>
                </div>`
            )
            .join("")
        : "<p>(no folders yet)</p>";

      adminContent.innerHTML = `
        <h3>📁 Manage Folders</h3>
        <div class="folder-actions" style="margin-bottom:10px;">
          <input id="new-folder-name" placeholder="Folder name" />
          <button id="create-folder-btn">➕ Create Folder</button>
          <button id="generate-ai-folders-btn">🤖 AI Organize</button>
        </div>
        <div id="folder-contents">${folderList}</div>
      `;

      // 🔹 Eventy przycisków
      document.getElementById("create-folder-btn")?.addEventListener("click", createFolder);
      document.getElementById("generate-ai-folders-btn")?.addEventListener("click", aiOrganizeFolders);

      // ✅ Naprawiony event kliknięcia w foldery
      const folderListEl = document.getElementById("folder-contents");
      folderListEl?.addEventListener("click", (e) => {
        const nameEl = e.target.closest(".folder-name");
        const delEl = e.target.closest(".delete-folder-btn");

        // klik w nazwę folderu → otwórz/zamknij
        if (nameEl && nameEl.dataset.folder) {
          openFolder(nameEl.dataset.folder);
          e.stopPropagation();
          return;
        }

        // klik w przycisk Delete → usuń
        if (delEl && delEl.dataset.folder) {
          deleteFolder(delEl.dataset.folder);
          e.stopPropagation();
          return;
        }
      });

      return;
    }

    // ==================
    // 🟡 UNKNOWN TAB
    // ==================
    adminContent.innerHTML = "<p>⚠️ Unknown tab selected.</p>";

  } catch (err) {
    console.error(`❌ showAdminTab(${tab}) error:`, err);
    adminContent.innerHTML = `<p>❌ Failed to load ${tab} data.<br><code>${err.message}</code></p>`;
  }
}
// ==========================
// 📁 FUNCTION: createFolder
// ==========================
async function createFolder() {
  const input = document.getElementById("new-folder-name");
  if (!input) return;
  const name = input.value.trim();
  if (!name) {
    alert("⚠️ Enter folder name.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/folders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    alert(data.message || "✅ Folder created.");
    input.value = "";
    await showAdminTab("folders");
  } catch (err) {
    console.error("❌ Folder create error:", err);
    alert("❌ Failed to create folder.");
  }
}
// ==========================
// 🗑️ FUNCTION: deleteFolder
// ==========================
async function deleteFolder(name) {
  if (!name) return;
  if (!confirm(`Delete folder '${name}'? This cannot be undone.`)) return;

  try {
    const res = await fetch(`${API_BASE}/folders/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    alert(data.message || "✅ Folder deleted.");
    await showAdminTab("folders");
  } catch (err) {
    console.error("❌ Delete folder error:", err);
    alert("❌ Failed to delete folder.");
  }
}
// ==========================
// 📂 FUNCTION: openFolder
// ==========================
async function openFolder(name) {
  const nameEl = document.querySelector(`.folder-name[data-folder="${CSS.escape(name)}"]`);
  if (!nameEl) return;

  const folderItem = nameEl.closest(".folder-item");
  if (!folderItem) return;

  const panelId = `panel_${name.replace(/[^a-zA-Z0-9_-]/g, "_")}`;
  let panel = document.getElementById(panelId);

  if (panel) {
    panel.style.display = panel.style.display === "none" ? "block" : "none";
    return;
  }

  panel = document.createElement("div");
  panel.id = panelId;
  panel.className = "folder-panel";
  panel.style.margin = "8px 0 16px 32px";
  panel.style.padding = "12px";
  panel.style.border = "1px solid #334155";
  panel.style.borderRadius = "8px";
  panel.style.background = "#0f172a";
  panel.innerHTML = `⏳ Loading contents of <strong>${name}</strong>...`;

  folderItem.insertAdjacentElement("afterend", panel);

  try {
    const res = await fetch(`${API_BASE}/folders/${encodeURIComponent(name)}`);
    if (!res.ok) throw new Error("Failed to load folder");
    const data = await res.json();

    if (!data.files?.length) {
      panel.innerHTML = `<p>📂 Folder <strong>${name}</strong> is empty.</p>`;
      return;
    }

    const fileList = data.files
      .map(
        (f) => `
          <div class="file-item" style="display:flex;align-items:center;gap:8px;margin:6px 0;">
            <span>📄 ${f}</span>
            <button onclick="viewPDF('${f}', '${name}')">👁️ View</button>
            <button onclick="downloadPDF('${f}', '${name}')">⬇️ Download</button>
            <button onclick="deletePDF('${f}', '${name}')" style="background:#b91c1c;color:#fff;">🗑️ Delete</button>
            <button
                      class="move-btn"
                      onclick="openMoveBetweenFolders('${name}', '${f}')"
                    >📁 Move between folders</button>
          </div>`
      )
      .join("");

    panel.innerHTML = `
      <h4 style="margin:0 0 8px;">Files in <strong>${name}</strong>:</h4>
      ${fileList}
    `;
  } catch (err) {
    console.error("❌ Folder load error:", err);
    panel.innerHTML = `<p>❌ Failed to load folder <strong>${name}</strong>.</p>`;
  }
}
// ==========================
// 🧩 EVENT: CLICK ON FOLDER NAME ONLY
// ==========================
document.addEventListener("click", (e) => {
  const folderNameEl = e.target.closest(".folder-name");
  if (folderNameEl && folderNameEl.dataset.folder) {
    openFolder(folderNameEl.dataset.folder);
  }
});
// ==========================
// 📁 FUNCTION: getAllFolders
// ==========================
// Fetches all folder names from backend (for dropdowns and moves)
async function getAllFolders() {
  try {
    const res = await fetch(`${API_BASE}/folders`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return Array.isArray(data.folders) ? data.folders : [];
  } catch (err) {
    console.error("❌ getAllFolders error:", err);
    return [];
  }
}
// ==========================
// 📦 FUNCTION: openMoveBetweenFolders
// ==========================
async function openMoveBetweenFolders(currentFolder, filename) {
  try {
    const folders = await getAllFolders();
    const available = folders.filter((f) => f !== currentFolder);
    if (!available.length) {
      alert("⚠️ No other folders available to move file.");
      return;
    }

    // Tworzymy modal
    const modal = document.createElement("div");
    modal.className = "modal";
    modal.innerHTML = `
      <div class="modal-content">
        <h3>📁 Move "${filename}"</h3>
        <p>Select destination folder:</p>
        <select id="target-folder" class="move-select">
          ${available.map((f) => `<option value="${f}">${f}</option>`).join("")}
        </select>
        <button id="confirm-move-btn">Move File</button>
        <button id="cancel-move-btn" style="background:#475569;color:#fff;">Cancel</button>
      </div>
    `;
    document.body.appendChild(modal);
    modal.style.display = "flex";

    // Obsługa przycisków
    document.getElementById("cancel-move-btn").onclick = () => modal.remove();
    document.getElementById("confirm-move-btn").onclick = async () => {
      const targetFolder = document.getElementById("target-folder").value;
      if (!targetFolder) return alert("⚠️ Choose a folder first.");
      await moveFileBetweenFolders(currentFolder, filename, targetFolder);
      modal.remove();
    };
  } catch (err) {
    console.error("❌ openMoveBetweenFolders error:", err);
    alert("❌ Failed to open move dialog.");
    await openFolder(targetFolder);
    await refreshAdmin();
  }
}

// ==========================
// 🚚 FUNCTION: moveFileBetweenFolders (with auto-refresh)
// ==========================
async function moveFileBetweenFolders(sourceFolder, filename, targetFolder) {
  try {
    console.log(`📂 Moving file '${filename}' from '${sourceFolder}' → '${targetFolder}'`);

    // Pokazujemy krótki komunikat o przenoszeniu
    const statusBox = document.getElementById("upload-result");
    if (statusBox) {
      statusBox.innerHTML = `⏳ Moving <strong>${filename}</strong> to <strong>${targetFolder}</strong>...`;
    }

    const res = await fetch(`${API_BASE}/folders/move`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename, folder: targetFolder }),
    });

    const data = await res.json();
    console.log("✅ Move response:", data);

    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);

    alert(`✅ File '${filename}' moved to '${targetFolder}'.`);

    // 🔄 Refresh folder panels
    const sourcePanelId = `panel_${sourceFolder.replace(/[^a-zA-Z0-9_-]/g, "_")}`;
    const targetPanelId = `panel_${targetFolder.replace(/[^a-zA-Z0-9_-]/g, "_")}`;

    // Usuń stary panel źródłowy
    const oldPanel = document.getElementById(sourcePanelId);
    if (oldPanel) oldPanel.remove();

    // Jeśli folder docelowy był otwarty, usuń też jego panel (żeby się odświeżył)
    const newPanel = document.getElementById(targetPanelId);
    if (newPanel) newPanel.remove();

    // 🔁 Otwórz ponownie foldery (aktualny stan)
    await openFolder(sourceFolder);
    await openFolder(targetFolder);

    // 🔁 Odśwież dashboard i listę dokumentów
    if (typeof refreshAdmin === "function") await refreshAdmin();
    if (typeof loadDocuments === "function") await loadDocuments();

    // ✅ Komunikat po zakończeniu
    if (statusBox) {
      statusBox.innerHTML = `✅ <strong>${filename}</strong> successfully moved to <strong>${targetFolder}</strong>.`;
    }

  } catch (err) {
    console.error("❌ moveFileBetweenFolders error:", err);
    alert(`❌ Failed to move file: ${err.message}`);
  }
}
// ==========================
// 🧩 FUNCTIONAL BLOCK: CLICK ON FOLDER
// ==========================
// Delegacja kliknięć — otwiera lub zwija zawartość folderu po kliknięciu jego nazwy
document.addEventListener("click", (e) => {
  const item = e.target.closest(".folder-item");
  if (item && item.dataset.folder) {
    console.log(`📂 Opening folder: ${item.dataset.folder}`);
    openFolder(item.dataset.folder);
  }
});
// ==========================
// 🤖 FUNCTION: aiOrganizeFolders (auto-create folder + move files)
// ==========================
async function aiOrganizeFolders() {
  const tidy = (s) => (typeof s === "string" ? s.trim() : s);

  try {
    const btn = document.getElementById("generate-ai-folders-btn");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "🤖 Organizing...";
    }

    // 1️⃣ Fetch AI suggestions
    const res = await fetch(`${API_BASE}/ai/suggest-dynamic-folders`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    console.log("🧠 AI Folder Suggestions:", data);

    const suggestions = Array.isArray(data.folders) ? data.folders : [];
    if (suggestions.length === 0) {
      alert("⚠️ No AI folder suggestions found.");
      return;
    }

    // 2️⃣ Render suggestions
    const html = `
      <h4>🤖 AI Suggested Folders:</h4>
      <p style="font-size:0.9em;color:#94a3b8;">Edit folder name, then click <strong>Add</strong> to create it and move files.</p>
      <ul>
        ${suggestions
          .map((sug, i) => {
            const folderName = tidy(sug.folder) || `Folder_${i + 1}`;
            const files = Array.isArray(sug.files) ? sug.files : [];

            const filesList = files.length
              ? `<ul style="margin:8px 0 0 24px;">${files
                  .map((f) => `<li>📄 ${f}</li>`)
                  .join("")}</ul>`
              : `<em style="color:#94a3b8;margin-left:24px;">No files suggested</em>`;

            return `
              <li class="ai-folder-suggestion" style="margin-bottom:10px;padding:10px;border:1px solid #334155;border-radius:8px;background:#1e293b;">
                <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;">
                  <div style="display:flex;align-items:center;gap:8px;">
                    <span>📁</span>
                    <span
                      class="editable-folder-name"
                      contenteditable="true"
                      data-files='${JSON.stringify(files)}'
                      style="outline:none;cursor:text;color:#38bdf8;user-select:text;"
                      title="Click to edit folder name"
                    >${folderName}</span>
                  </div>
                  <button
                    class="add-folder-btn"
                    style="background:#22c55e;color:#0f172a;border:none;border-radius:6px;padding:6px 12px;cursor:pointer;font-weight:700;"
                  >➕ Add</button>
                </div>
                ${filesList}
                <div class="ai-move-log" style="margin-top:8px;font-size:.9em;color:#94a3b8;"></div>
              </li>
            `;
          })
          .join("")}
      </ul>
    `;

    const container = document.getElementById("folder-contents");
    if (container) container.innerHTML = html;

    // 3️⃣ Handle "Add" (create + move)
    document.querySelectorAll(".add-folder-btn").forEach((addBtn) => {
      addBtn.addEventListener("click", async (e) => {
        const item = e.target.closest(".ai-folder-suggestion");
        const nameEl = item.querySelector(".editable-folder-name");
        const moveLog = item.querySelector(".ai-move-log");
        const newName = tidy(nameEl?.textContent);

        const files = (() => {
          try {
            const parsed = JSON.parse(nameEl?.dataset.files || "[]");
            return Array.isArray(parsed) ? parsed.map(tidy).filter(Boolean) : [];
          } catch {
            return [];
          }
        })();

        if (!newName) {
          alert("⚠️ Folder name cannot be empty.");
          return;
        }

        e.target.disabled = true;
        e.target.textContent = "Working…";

        try {
          // 1️⃣ Create folder if not exists
          const resCreate = await fetch(`${API_BASE}/folders`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: newName }),
          });
          const dataCreate = await resCreate.json();
          if (!resCreate.ok && !dataCreate?.detail?.includes("already exists")) {
            throw new Error(dataCreate.detail || "Folder creation failed");
          }

          // 2️⃣ Move each file
          let ok = 0;
          let fail = 0;
          for (const file of files) {
            try {
              const moveRes = await fetch(`${API_BASE}/folders/move`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filename: file, folder: newName }),
              });
              if (moveRes.ok) ok++;
              else fail++;
            } catch {
              fail++;
            }
            moveLog.textContent = `Moved ${ok}/${files.length} files (failed: ${fail})`;
          }

          alert(`✅ Folder '${newName}' ready — moved ${ok}/${files.length} files.`);
          await showAdminTab("folders");
        } catch (err) {
          console.error("❌ Folder creation/move error:", err);
          alert("❌ Failed to create folder or move files.");
        } finally {
          e.target.disabled = false;
          e.target.textContent = "➕ Add";
        }
      });
    });
  } catch (err) {
    console.error("❌ AI folder organization error:", err);
    alert("❌ Failed to generate AI folder suggestions.");
  } finally {
    const btn = document.getElementById("generate-ai-folders-btn");
    if (btn) {
      btn.disabled = false;
      btn.textContent = "🤖 AI Organize";
    }
  }
}

// ==========================
// ➕ FUNCTION: addFileToSuggestedFolder (fixed endpoint URL)
// ==========================
// Called when user clicks "Add here" in AI Organizer suggestion list
async function addFileToSuggestedFolder(folderName, filename) {
  try {
    const btn = document.querySelector(
      `.add-file-btn[data-file="${CSS.escape(filename)}"][data-folder="${CSS.escape(folderName)}"]`
    );
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Moving…";
    }

    // ✅ Correct endpoint: /folders/move
    const res = await fetch(`${API_BASE}/folders/move`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename, folder: folderName }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    console.log("✅ Move-to-folder:", data);

    // 🔄 Refresh UI sections
    if (typeof showAdminTab === "function") await showAdminTab("folders");
    if (typeof loadDocuments === "function") await loadDocuments();
    if (typeof refreshAdmin === "function") await refreshAdmin();

    alert(`✅ File '${filename}' moved to '${folderName}'.`);
  } catch (err) {
    console.error("❌ Move file (AI) error:", err);
    alert(`❌ Failed to move '${filename}' to '${folderName}'.`);
  }
}
// ==========================
// 💬 FUNCTION: Ask AI (Main Page Only)
// ==========================
// Handles AI question modal on the main page (not in admin panel)
document.addEventListener("DOMContentLoaded", () => {
  const askAiBtn = document.getElementById("ask-ai-btn");
  const modal = document.getElementById("ask-ai-modal");
  const closeBtn = document.getElementById("ai-close-btn");
  const sendBtn = document.getElementById("ai-send-btn");
  const queryInput = document.getElementById("ai-query");
  const answerBox = document.getElementById("ai-answer");

  // 🧠 Open modal
  askAiBtn?.addEventListener("click", () => {
    modal.style.display = "flex";
    answerBox.innerHTML = "";
    queryInput.value = "";
    queryInput.focus();
  });

  // ❌ Close modal
  closeBtn?.addEventListener("click", () => {
    modal.style.display = "none";
  });

  // 🖱️ Close on outside click
  window.addEventListener("click", (e) => {
    if (e.target === modal) modal.style.display = "none";
  });

  // 🚀 Send question to backend AI
  sendBtn?.addEventListener("click", async () => {
    const question = queryInput.value.trim();
    if (!question) {
      answerBox.textContent = "⚠️ Please enter a question.";
      return;
    }

    answerBox.textContent = "⏳ Thinking...";

    try {
      const res = await fetch(`${API_BASE}/ai/query?text=${encodeURIComponent(question)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      console.log("🤖 AI Response:", data);

      // Handle AI answer gracefully
      let answerText = "";
      let sourcesHTML = "";

      if (typeof data.answer === "string") {
        answerText = data.answer;
      } else if (data.answer && typeof data.answer === "object") {
        answerText = data.answer.answer || JSON.stringify(data.answer, null, 2);
        if (Array.isArray(data.answer.sources)) {
          sourcesHTML = `<p><strong>📄 Sources:</strong> ${data.answer.sources.join(", ")}</p>`;
        }
      } else {
        answerText = "(No valid AI response)";
      }

      // Render result nicely
      answerBox.innerHTML = `
        <p><strong>🧠 Question:</strong> ${question}</p>
        <p><strong>🤖 Answer:</strong> ${answerText}</p>
        ${sourcesHTML}
      `;
    } catch (err) {
      console.error("❌ AI Query Error:", err);
      answerBox.textContent = "❌ Failed to get AI response. Please try again.";
    }
  });
});
// ==========================
// 🚀 FUNCTION: INIT / Startup Section
// ==========================
// Runs automatically after DOM is fully loaded.
// Initializes uploads, loads documents, refreshes admin dashboard,
// and populates folder dropdowns.
document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 Initializing SmartDocFinder frontend...");

  const uploadForm = document.getElementById("upload-form");
  const refreshBtn = document.getElementById("refresh-btn");

  // 🎯 Bind upload form submit
  if (uploadForm) {
    uploadForm.addEventListener("submit", handleUpload);
  }

  // 🔄 Bind refresh button to reload document list
  if (refreshBtn) {
    refreshBtn.addEventListener("click", async () => {
      console.log("🔁 Refreshing document list...");
      await loadDocuments();
      await refreshAdmin();
    });
  }

  // 📂 Initialize folder dropdowns if they exist
  populateFolderDropdowns();

  // 🧾 Load initial document list
  loadDocuments();

  // 🧠 Refresh admin dashboard
  refreshAdmin();

  console.log("✅ SmartDocFinder initialization complete.");
});
// ==========================
// 🧠 FUNCTION: Elasticsearch Index Management
// ==========================
// Handles "Clear Index" and "Reindex All" buttons from the main page.
// Works independently of the admin panel.
document.addEventListener("click", async (e) => {
  // 🧹 CLEAR INDEX
  if (e.target && e.target.id === "clear-index-btn") {
    if (!confirm("🧹 Do you really want to clear the entire Elasticsearch index?")) return;

    const btn = e.target;
    btn.disabled = true;
    btn.textContent = "Clearing…";

    try {
      const res = await fetch(`${API_BASE}/clear-index`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      alert(data.message || "✅ Elasticsearch index cleared successfully.");
      await refreshAdmin();
    } catch (err) {
      console.error("❌ Clear index error:", err);
      alert("❌ Failed to clear Elasticsearch index.");
    } finally {
      btn.disabled = false;
      btn.textContent = "Clear Elasticsearch Index";
    }
  }

  // 🔁 REINDEX ALL
  if (e.target && e.target.id === "reindex-btn") {
    if (!confirm("🔁 Reindex all documents in Elasticsearch?")) return;

    const btn = e.target;
    btn.disabled = true;
    btn.textContent = "Reindexing…";

    try {
      const res = await fetch(`${API_BASE}/reindex-all`, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      alert(data.message || "✅ Reindex completed successfully.");
      await refreshAdmin();
    } catch (err) {
      console.error("❌ Reindex error:", err);
      alert("❌ Failed to reindex documents.");
    } finally {
      btn.disabled = false;
      btn.textContent = "Reindex All PDFs";
    }
  }
});

// =======================================
// ⚙️ INIT ADMIN DASHBOARD EVENTS
// =======================================
document.addEventListener("DOMContentLoaded", () => {
  const refreshBtn = document.getElementById("admin-refresh");
  const autoRefreshChk = document.getElementById("admin-auto");

  // ✅ Manual refresh
  if (refreshBtn) {
    refreshBtn.addEventListener("click", async () => {
      refreshBtn.disabled = true;
      refreshBtn.textContent = "⏳ Refreshing...";
      try {
        await refreshAdmin();
      } catch (e) {
        console.error("Manual refresh error:", e);
      }
      refreshBtn.textContent = "🔁 Refresh Status";
      refreshBtn.disabled = false;
    });
  }

  // 🔄 Auto-refresh every 15 seconds
  if (autoRefreshChk) {
    let refreshInterval = null;

    autoRefreshChk.addEventListener("change", () => {
      if (autoRefreshChk.checked) {
        console.log("✅ Auto-refresh enabled (15s)");
        refreshAdmin(); // immediate first run
        refreshInterval = setInterval(refreshAdmin, 15000);
      } else {
        console.log("🛑 Auto-refresh stopped");
        clearInterval(refreshInterval);
        refreshInterval = null;
      }
    });
  }
});