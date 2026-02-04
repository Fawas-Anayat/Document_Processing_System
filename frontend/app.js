const els = {
  apiBase: document.getElementById("apiBase"),
  saveBase: document.getElementById("saveBase"),
  signupForm: document.getElementById("signupForm"),
  loginForm: document.getElementById("loginForm"),
  refreshBtn: document.getElementById("refreshBtn"),
  logoutBtn: document.getElementById("logoutBtn"),
  uploadForm: document.getElementById("uploadForm"),
  showDocsBtn: document.getElementById("showDocsBtn"),
  chatForm: document.getElementById("chatForm"),
  signupOutput: document.getElementById("signupOutput"),
  loginOutput: document.getElementById("loginOutput"),
  refreshOutput: document.getElementById("refreshOutput"),
  logoutOutput: document.getElementById("logoutOutput"),
  uploadOutput: document.getElementById("uploadOutput"),
  docsOutput: document.getElementById("docsOutput"),
  chatOutput: document.getElementById("chatOutput"),
  chatAnswer: document.getElementById("chatAnswer"),
  docsList: document.getElementById("docsList"),
  accessToken: document.getElementById("accessToken"),
  refreshToken: document.getElementById("refreshToken"),
  requestLog: document.getElementById("requestLog"),
  clearLog: document.getElementById("clearLog"),
};

const storageKey = "dps_api_base";
const accessKey = "dps_access_token";
const refreshKey = "dps_refresh_token";

const state = {
  apiBase: localStorage.getItem(storageKey) || els.apiBase.value,
};

els.apiBase.value = state.apiBase;
els.accessToken.value = localStorage.getItem(accessKey) || "";
els.refreshToken.value = localStorage.getItem(refreshKey) || "";

function setTokens(tokens) {
  if (tokens?.access_token) {
    els.accessToken.value = tokens.access_token;
    localStorage.setItem(accessKey, tokens.access_token);
  }
  if (tokens?.refresh_token) {
    els.refreshToken.value = tokens.refresh_token;
    localStorage.setItem(refreshKey, tokens.refresh_token);
  }
}

function logRequest(label, payload) {
  const timestamp = new Date().toLocaleTimeString();
  const entry = `[${timestamp}] ${label}\n${payload}\n\n`;
  els.requestLog.textContent = entry + els.requestLog.textContent;
}

function pretty(data) {
  return JSON.stringify(data, null, 2);
}

async function apiFetch(path, options = {}) {
  const url = `${state.apiBase}${path}`;
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  let body;
  if (contentType.includes("application/json")) {
    body = await response.json();
  } else {
    body = await response.text();
  }

  if (!response.ok) {
    const message = typeof body === "string" ? body : body?.detail || body;
    throw new Error(message || "Request failed");
  }

  return body;
}

function authHeaders() {
  const token = els.accessToken.value.trim();
  if (!token) {
    throw new Error("Missing access token. Login first.");
  }
  return { Authorization: `Bearer ${token}` };
}

els.saveBase.addEventListener("click", () => {
  state.apiBase = els.apiBase.value.trim() || state.apiBase;
  localStorage.setItem(storageKey, state.apiBase);
  logRequest("API base updated", state.apiBase);
});

els.signupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    name: document.getElementById("signupName").value.trim(),
    email: document.getElementById("signupEmail").value.trim(),
    password: document.getElementById("signupPassword").value.trim(),
  };

  els.signupOutput.textContent = "Sending...";
  try {
    logRequest("POST /Signup", pretty(payload));
    const data = await apiFetch("/Signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    els.signupOutput.textContent = pretty(data);
  } catch (error) {
    els.signupOutput.textContent = error.message;
  }
});

els.loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new URLSearchParams();
  form.append("username", document.getElementById("loginEmail").value.trim());
  form.append("password", document.getElementById("loginPassword").value.trim());

  els.loginOutput.textContent = "Sending...";
  try {
    logRequest("POST /login", form.toString());
    const data = await apiFetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });
    setTokens(data);
    els.loginOutput.textContent = pretty(data);
  } catch (error) {
    els.loginOutput.textContent = error.message;
  }
});

els.refreshBtn.addEventListener("click", async () => {
  els.refreshOutput.textContent = "Sending...";
  try {
    const payload = { refresh_token: els.refreshToken.value.trim() };
    logRequest("POST /refresh", pretty(payload));
    const data = await apiFetch("/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setTokens(data);
    els.refreshOutput.textContent = pretty(data);
  } catch (error) {
    els.refreshOutput.textContent = error.message;
  }
});

els.logoutBtn.addEventListener("click", async () => {
  els.logoutOutput.textContent = "Sending...";
  try {
    const payload = { refresh_token: els.refreshToken.value.trim() };
    logRequest("POST /logout", pretty(payload));
    const data = await apiFetch("/logout", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload),
    });
    els.logoutOutput.textContent = pretty(data);
  } catch (error) {
    els.logoutOutput.textContent = error.message;
  }
});

els.uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const fileInput = document.getElementById("fileInput");
  const file = fileInput.files[0];
  if (!file) {
    els.uploadOutput.textContent = "Select a file to upload.";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  els.uploadOutput.textContent = "Uploading...";
  try {
    logRequest("POST /uploadFile", `file=${file.name} (${file.type})`);
    const data = await apiFetch("/uploadFile", {
      method: "POST",
      headers: { ...authHeaders() },
      body: formData,
    });
    els.uploadOutput.textContent = pretty(data);
  } catch (error) {
    els.uploadOutput.textContent = error.message;
  }
});

els.showDocsBtn.addEventListener("click", async () => {
  els.docsOutput.textContent = "Loading...";
  els.docsList.innerHTML = "";
  try {
    logRequest("POST /ShowDocuments", "Bearer auth");
    const data = await apiFetch("/ShowDocuments", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
    });
    els.docsOutput.textContent = pretty(data);
    const docs = data?.documents || [];
    docs.forEach((doc) => {
      const card = document.createElement("div");
      card.className =
        "rounded-2xl border border-[#e1d7cd] bg-clay-50/70 px-4 py-3 text-sm text-neutral-700";
      card.innerHTML = `
        <h3 class="font-sans text-base font-semibold text-neutral-800">Document #${doc.file_id}</h3>
        <p class="mt-1 text-xs uppercase tracking-[0.2em] text-neutral-500">Collection</p>
        <p class="text-sm text-neutral-700">${doc.collection_name}</p>
        <p class="mt-2 text-xs uppercase tracking-[0.2em] text-neutral-500">Chunks</p>
        <p class="text-sm text-neutral-700">${doc.chunk_count}</p>
      `;
      els.docsList.appendChild(card);
    });
  } catch (error) {
    els.docsOutput.textContent = error.message;
  }
});

els.chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    document_id: Number(document.getElementById("chatDocId").value),
    query: document.getElementById("chatQuery").value.trim(),
  };

  els.chatOutput.textContent = "Asking...";
  els.chatAnswer.textContent = "";
  try {
    logRequest("POST /chat", pretty(payload));
    const data = await apiFetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload),
    });
    els.chatOutput.textContent = pretty(data);
    els.chatAnswer.textContent = data?.answer || "No answer returned.";
  } catch (error) {
    els.chatOutput.textContent = error.message;
  }
});

els.clearLog.addEventListener("click", () => {
  els.requestLog.textContent = "";
});
