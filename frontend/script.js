const uploadForm = document.getElementById('upload-form');
const uploadResult = document.getElementById('upload-result');
const documentsList = document.getElementById('documents-list');
const refreshBtn = document.getElementById('refresh-btn');
const searchBtn = document.getElementById('search-btn');

uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];

    if (!file) {
        uploadResult.textContent = "⚠️ Please select a file first.";
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("http://127.0.0.1:8000/documents/upload-pdf", {
            method: "POST",
            body: formData
        });

        if (res.ok) {
            const data = await res.json();
            uploadResult.textContent = "✅ File uploaded successfully: " + data.filename;
            loadDocuments();
        } else {
            const err = await res.json().catch(()=>null);
            uploadResult.textContent = "❌ Upload failed. " + (err ? JSON.stringify(err) : "");
        }
    } catch (error) {
        uploadResult.textContent = "❌ Server error. Check logs.";
        console.error(error);
    }
});

async function loadDocuments() {
    documentsList.innerHTML = "";
    try {
        const res = await fetch("http://127.0.0.1:8000/documents/");
        if (res.ok) {
            const docs = await res.json(); // expects an array
            docs.forEach(doc => {
                const li = document.createElement("li");
                li.textContent = `${doc.filename}`;
                // add view and delete buttons
                const viewBtn = document.createElement("button");
                viewBtn.textContent = "View";
                viewBtn.addEventListener("click", () => {
                    window.open(`http://127.0.0.1:8000/documents/file/${encodeURIComponent(doc.filename)}`, "_blank");
                });
                const delBtn = document.createElement("button");
                delBtn.textContent = "Delete";
                delBtn.addEventListener("click", async () => {
                    await fetch(`http://127.0.0.1:8000/documents/delete/${encodeURIComponent(doc.filename)}`, { method: "DELETE" });
                    loadDocuments();
                });
                li.appendChild(viewBtn);
                li.appendChild(delBtn);
                documentsList.appendChild(li);
            });
        } else {
            documentsList.innerHTML = "<li>Could not load documents</li>";
        }
    } catch (e) {
        documentsList.innerHTML = "<li>Server error</li>";
    }
}

refreshBtn.addEventListener('click', loadDocuments);

searchBtn.addEventListener('click', async () => {
    const query = document.getElementById('search-query').value.trim();
    const searchResults = document.getElementById('search-results');
    searchResults.innerHTML = "";

    if (!query) return;

    const res = await fetch(`http://127.0.0.1:8000/documents/search?query=${encodeURIComponent(query)}`);
    if (res.ok) {
        const results = await res.json();
        if (results.length === 0) {
            const li = document.createElement("li");
            li.textContent = "No results found.";
            searchResults.appendChild(li);
            return;
        }
        results.forEach(r => {
            const li = document.createElement("li");
            li.innerHTML = `<strong>${r.filename}</strong> — ${r.snippet}`;
            searchResults.appendChild(li);
        });
    } else {
        const li = document.createElement("li");
        li.textContent = "No results found.";
        searchResults.appendChild(li);
    }
});

loadDocuments();