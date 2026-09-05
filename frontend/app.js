const API = (
  window.APP_CONFIG?.API_BASE_URL ||
  "http://localhost:8000"
).replace(/\/$/, "");


let token = localStorage.getItem("contractai_token");

let authMode = "login";

let currentContract = null;


/* ============================================================
   DOM HELPERS
   ============================================================ */

const $ = (selector) => document.querySelector(selector);


const show = (element, yes = true) => {
  if (!element) return;

  element.classList.toggle("hidden", !yes);
};


/* ============================================================
   TOAST
   ============================================================ */

const toast = (message) => {

  const element = $("#toast");

  if (!element) return;

  element.textContent = message;

  element.classList.remove("hidden");

  setTimeout(() => {
    element.classList.add("hidden");
  }, 3200);
};


/* ============================================================
   DATE FORMAT
   ============================================================ */

const fmtDate = (value) => {
  return new Date(value).toLocaleString();
};


/* ============================================================
   BACKGROUND STAGE
   ============================================================

   Login:
     login-background.png
   Authenticated application:
     dashboard-background.jpg

   The image is applied to #pageStage only.
   The topbar and footer remain outside of it.
   ============================================================ */

function setPageStage(mode) {

  const stage = $("#pageStage");

  if (!stage) return;

  stage.classList.remove(
    "login-stage",
    "dashboard-stage"
  );

  if (mode === "login") {

    stage.classList.add("login-stage");

  } else {

    stage.classList.add("dashboard-stage");

  }
}


/* ============================================================
   API
   ============================================================ */

async function api(path, options = {}) {

  const headers = new Headers(
    options.headers || {}
  );


  if (token) {
    headers.set(
      "Authorization",
      `Bearer ${token}`
    );
  }


  const response = await fetch(
    API + path,
    {
      ...options,
      headers
    }
  );


  if (!response.ok) {

    let detail = "Request failed";


    try {

      const json = await response.json();

      detail = json.detail || detail;

    } catch (_) {
      // Ignore JSON parsing errors.
    }


    if (response.status === 401) {
      logout();
    }


    throw new Error(detail);
  }


  const contentType =
    response.headers.get("content-type") || "";


  return contentType.includes("application/json")
    ? response.json()
    : response.blob();
}


/* ============================================================
   AUTHENTICATION
   ============================================================ */

function setToken(data) {

  token = data.access_token;

  localStorage.setItem(
    "contractai_token",
    token
  );
}


function logout() {

  token = null;

  localStorage.removeItem(
    "contractai_token"
  );


  show($("#appView"), false);

  show($("#detailView"), false);

  show($("#authView"), true);


  $("#userArea").innerHTML = "";


  /*
   * Return the background to the login image.
   */
  setPageStage("login");
}


function renderAuth() {

  show($("#authView"), true);

  show($("#appView"), false);

  show($("#detailView"), false);


  $("#userArea").innerHTML = "";


  /*
   * Login page background.
   */
  setPageStage("login");
}


function renderApp(email = "") {

  show($("#authView"), false);

  show($("#detailView"), false);

  show($("#appView"), true);


  /*
   * Dashboard background.
   */
  setPageStage("dashboard");


  $("#userArea").innerHTML = `
    <span class="muted small">
      ${escapeHtml(email || "Signed in")}
    </span>

    <button
      class="secondary"
      id="logoutBtn"
      type="button"
    >
      Sign out
    </button>
  `;


  $("#logoutBtn").onclick = logout;


  loadContracts();
}


/* ============================================================
   LOGIN / SIGNUP TABS
   ============================================================ */

document
  .querySelectorAll(".tab")
  .forEach((button) => {

    button.onclick = () => {

      authMode = button.dataset.auth;


      document
        .querySelectorAll(".tab")
        .forEach((tab) => {

          tab.classList.toggle(
            "active",
            tab === button
          );

        });


      $("#authSubmit").textContent =
        authMode === "login"
          ? "Sign in"
          : "Create account";


      $("#password").autocomplete =
        authMode === "login"
          ? "current-password"
          : "new-password";

    };

  });


/* ============================================================
   LOGIN / SIGNUP SUBMIT
   ============================================================ */

$("#authForm").onsubmit = async (event) => {

  event.preventDefault();


  try {

    const data = await api(
      `/api/v1/auth/${authMode}`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json"
        },

        body: JSON.stringify({
          email: $("#email").value,
          password: $("#password").value
        })
      }
    );


    setToken(data);

    renderApp(data.email);

  } catch (error) {

    toast(error.message);

  }

};


/* ============================================================
   LOAD CONTRACTS
   ============================================================ */

async function loadContracts() {

  try {

    const rows = await api(
      "/api/v1/contracts"
    );


    $("#contractCount").textContent =
      rows.length;


    $("#stats").innerHTML = `
      <div class="stat">
        <span>Total contracts</span>
        <strong>${rows.length}</strong>
      </div>

      <div class="stat">
        <span>Stored documents</span>
        <strong>${rows.length}</strong>
      </div>

      <div class="stat">
        <span>Supported formats</span>
        <strong>3</strong>
      </div>
    `;


    const box = $("#contracts");


    if (!rows.length) {

      box.innerHTML = `
        <p class="muted">
          No contracts stored yet.
        </p>
      `;

      return;
    }


    box.innerHTML = rows
      .map((contract) => {

        return `
          <div class="contract-row">

            <div>

              <div class="contract-name">
                ${escapeHtml(contract.filename)}
              </div>

              <div class="contract-meta">
                ${escapeHtml(contract.status)}
                · ${fmtDate(contract.created_at)}
                · ${(contract.file_size / 1024 / 1024).toFixed(2)} MB
              </div>

            </div>


            <div class="row-actions">

              <button
                class="secondary"
                type="button"
                onclick="openContract(${contract.id})"
              >
                Open
              </button>

            </div>

          </div>
        `;

      })
      .join("");


  } catch (error) {

    toast(error.message);

  }

}


/* ============================================================
   HTML ESCAPING
   ============================================================ */

function escapeHtml(value) {

  return String(value).replace(
    /[&<>'"]/g,
    (character) => {

      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "'": "&#39;",
        '"': "&quot;"
      }[character];

    }
  );

}


/* ============================================================
   REFRESH
   ============================================================ */

$("#refreshBtn").onclick = loadContracts;


/* ============================================================
   FILE UPLOAD
   ============================================================ */

let selectedFile = null;


$("#fileInput").onchange = (event) => {

  selectedFile =
    event.target.files[0] || null;

  updateFile();

};


$("#dropzone").ondragover = (event) => {

  event.preventDefault();

};


$("#dropzone").ondrop = (event) => {

  event.preventDefault();


  selectedFile =
    event.dataTransfer.files[0] || null;


  updateFile();

};


function updateFile() {

  const element = $("#selectedFile");


  if (selectedFile) {

    show(element, true);


    element.textContent =
      `${selectedFile.name} · ${(selectedFile.size / 1024 / 1024).toFixed(2)} MB`;


    $("#uploadBtn").disabled = false;

  } else {

    show(element, false);

    $("#uploadBtn").disabled = true;

  }

}


/* ============================================================
   STORE CONTRACT
   ============================================================ */

$("#uploadBtn").onclick = async () => {

  if (!selectedFile) {
    return;
  }


  const formData = new FormData();

  formData.append(
    "file",
    selectedFile
  );


  try {

    const contract = await api(
      "/api/v1/contracts",
      {
        method: "POST",
        body: formData
      }
    );


    toast(
      "Contract stored securely in PostgreSQL"
    );


    selectedFile = null;

    $("#fileInput").value = "";

    updateFile();

    await loadContracts();

    openContract(contract.id);


  } catch (error) {

    toast(error.message);

  }

};


/* ============================================================
   OPEN CONTRACT
   ============================================================ */

window.openContract = async (id) => {

  try {

    /*
     * Load contract details.
     */
    try {

      currentContract = await api(
        `/api/v1/contracts/${id}`
      );

    } catch (_) {

      /*
       * Fallback to the contract list.
       */
      const rows = await api(
        "/api/v1/contracts"
      );

      currentContract =
        rows.find(
          (contract) => contract.id === id
        );

    }


    if (!currentContract) {

      throw new Error(
        "Contract not found"
      );

    }


    $("#detailTitle").textContent =
      currentContract.filename;


    $("#detailMeta").textContent =
      `${currentContract.status} · ${fmtDate(currentContract.created_at)} · ${(currentContract.file_size / 1024 / 1024).toFixed(2)} MB`;


    show($("#appView"), false);

    show($("#detailView"), true);


    /*
     * Keep dashboard background on
     * contract-detail page.
     */
    setPageStage("dashboard");


    await loadAnalysis();


  } catch (error) {

    toast(error.message);

  }

};


/* ============================================================
   BACK TO DASHBOARD
   ============================================================ */

$("#backBtn").onclick = () => {

  show($("#detailView"), false);

  show($("#appView"), true);


  /*
   * Dashboard background remains active.
   */
  setPageStage("dashboard");


  loadContracts();

};


/* ============================================================
   VIEW ORIGINAL FILE
   ============================================================ */

$("#openFileBtn").onclick = async () => {

  try {

    const blob = await api(
      `/api/v1/contracts/${currentContract.id}/file`
    );


    const url =
      URL.createObjectURL(blob);


    window.open(
      url,
      "_blank"
    );


    setTimeout(
      () => URL.revokeObjectURL(url),
      60000
    );


  } catch (error) {

    toast(error.message);

  }

};


/* ============================================================
   DELETE CONTRACT
   ============================================================ */

$("#deleteBtn").onclick = async () => {

  if (
    !confirm(
      "Delete this stored contract and its analyses?"
    )
  ) {

    return;

  }


  try {

    await api(
      `/api/v1/contracts/${currentContract.id}`,
      {
        method: "DELETE"
      }
    );


    toast(
      "Contract deleted"
    );


    $("#backBtn").click();


  } catch (error) {

    toast(error.message);

  }

};


/* ============================================================
   ANALYZE CONTRACT
   ============================================================ */

$("#analyzeBtn").onclick = async () => {

  const button =
    $("#analyzeBtn");


  button.disabled = true;

  button.textContent =
    "Analyzing…";


  try {

    await api(
      `/api/v1/contracts/${currentContract.id}/analyze`,
      {
        method: "POST"
      }
    );


    toast(
      "Analysis completed"
    );


    await loadAnalysis();


  } catch (error) {

    toast(error.message);


  } finally {

    button.disabled = false;

    button.textContent =
      "Analyze contract";

  }

};


/* ============================================================
   LOAD ANALYSIS
   ============================================================ */

async function loadAnalysis() {

  try {

    const analysis = await api(
      `/api/v1/contracts/${currentContract.id}/analysis`
    );


    show(
      $("#analysisEmpty"),
      false
    );


    show(
      $("#analysisView"),
      true
    );


    $("#analysisStats").innerHTML = `
      <div class="stat">
        <span>Clauses</span>
        <strong>${analysis.clause_count}</strong>
      </div>

      <div class="stat">
        <span>Human review</span>
        <strong>${analysis.review_count}</strong>
      </div>

      <div class="stat">
        <span>Potential indicators</span>
        <strong>${analysis.risk_count}</strong>
      </div>
    `;


    $("#clauses").innerHTML =
      analysis.clauses
        .map((clause) => renderClause(clause))
        .join("");


  } catch (error) {

    if (
      error.message.includes(
        "No analysis"
      )
    ) {

      show(
        $("#analysisEmpty"),
        true
      );


      show(
        $("#analysisView"),
        false
      );

    } else {

      toast(error.message);

    }

  }

}


/* ============================================================
   RENDER CLAUSE
   ============================================================ */

function renderClause(clause) {

  const category =
    clause.predicted_category ||
    "Needs human review";


  const predictions =
    (clause.top_predictions || [])
      .map((prediction) => {

        return `
          <span class="prediction">
            ${escapeHtml(prediction.category)}
            · ${(prediction.probability * 100).toFixed(1)}%
          </span>
        `;

      })
      .join("");


  const risks =
    (clause.risks || [])
      .map((risk) => {

        return `
          <div
            class="risk ${escapeHtml(
              String(risk.severity).toLowerCase()
            )}"
          >

            <strong>
              ${escapeHtml(risk.rule_id)}
              · ${escapeHtml(risk.category)}
              · ${escapeHtml(risk.severity)}
            </strong>

            <p>
              ${escapeHtml(risk.explanation)}
            </p>

            <div class="evidence">
              ${escapeHtml(risk.evidence)}
            </div>

          </div>
        `;

      })
      .join("");


  const noRiskMessage =
    !clause.risks ||
    !clause.risks.length
      ? `
        <p class="muted small">
          No configured indicator triggered.
          This does not mean the clause is risk-free.
        </p>
      `
      : "";


  return `
    <article class="clause">

      <div class="clause-head">

        <div>

          <span class="category">
            Clause ${clause.clause_number}
            · ${escapeHtml(category)}
          </span>

          <div class="contract-meta">
            Model probability
            ${(clause.model_probability * 100).toFixed(1)}%
            · margin
            ${(clause.margin * 100).toFixed(1)}%
          </div>

        </div>


        ${
          clause.needs_human_review
            ? `
              <span class="review">
                HUMAN REVIEW
              </span>
            `
            : ""
        }

      </div>


      <div class="clause-body">

        <p>
          ${escapeHtml(clause.clause_text)}
        </p>


        <div class="predictions">
          ${predictions}
        </div>


        ${risks}

        ${noRiskMessage}

      </div>

    </article>
  `;

}


/* ============================================================
   INITIAL APPLICATION STATE
   ============================================================ */

if (token) {

  /*
   * Existing login token:
   * show dashboard and dashboard background.
   */
  renderApp();

} else {

  /*
   * No token:
   * show login and login background.
   */
  renderAuth();

}