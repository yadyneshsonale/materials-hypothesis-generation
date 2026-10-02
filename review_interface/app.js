const state = {
  papers: [],
  paper: null,
  activeRole: "all",
};

const $ = (id) => document.getElementById(id);

function make(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function pdfUrl(item) {
  const base = state.paper.pdf_url;
  if (!item || !item.pdf_page) return base;
  const search = item.evidence_spans?.[0]?.slice(0, 100) || "";
  return `${base}#page=${item.pdf_page}&search=${encodeURIComponent(search)}`;
}

function showEvidence(item, title) {
  document.querySelectorAll(".card.selected").forEach((card) => card.classList.remove("selected"));
  if (item.card) item.card.classList.add("selected");
  $("evidenceTitle").textContent = title;
  const body = $("evidenceBody");
  body.replaceChildren();
  const contexts = item.contexts || [];
  if (!contexts.length) {
    body.append(make("div", "empty", "No exact evidence span was attached."));
  }
  contexts.forEach((context, index) => {
    const chunk = make("div", "evidence-chunk");
    chunk.append(document.createTextNode(context.before ? `${context.before} ` : ""));
    const mark = make("mark", "", context.highlight);
    chunk.append(mark);
    chunk.append(document.createTextNode(context.after ? ` ${context.after}` : ""));
    if (!context.grounded) {
      chunk.prepend(make("div", "badge", `Unmatched span ${index + 1}`));
    }
    body.append(chunk);
  });
  $("evidenceDrawer").classList.add("open");
  $("pdfViewer").src = pdfUrl(item);
  $("openPdf").href = pdfUrl(item);
  $("pdfPageLabel").textContent = item.pdf_page ? `PDF · matched page ${item.pdf_page}` : "PDF · page match unavailable";
}

function renderRoleFilters() {
  const container = $("roleFilters");
  container.replaceChildren();
  const roles = [...new Set(state.paper.roles.map((item) => item.role))].sort();
  ["all", ...roles].forEach((role) => {
    const label = role === "all" ? "All roles" : role.replaceAll("_", " ");
    const button = make("button", `filter${state.activeRole === role ? " active" : ""}`, label);
    button.addEventListener("click", () => {
      state.activeRole = role;
      renderRoles();
      renderRoleFilters();
    });
    container.append(button);
  });
}

function renderRoles() {
  const container = $("rolesPanel");
  container.replaceChildren();
  const roles = state.paper.roles.filter(
    (item) => state.activeRole === "all" || item.role === state.activeRole,
  );
  if (!roles.length) {
    container.append(make("div", "empty", "No role claims match this filter."));
    return;
  }
  roles.forEach((item) => {
    const card = make("button", "card");
    const top = make("div", "card-top");
    top.append(make("span", "badge", item.role.replaceAll("_", " ")));
    top.append(make("span", "page", item.pdf_page ? `PDF p. ${item.pdf_page}` : "XML evidence"));
    card.append(top, make("p", "", item.content));
    card.addEventListener("click", () => {
      item.card = card;
      showEvidence(item, `${item.role.replaceAll("_", " ")} · ${item.id}`);
    });
    container.append(card);
  });
}

function renderQuestions() {
  const container = $("questionsPanel");
  container.replaceChildren();
  if (!state.paper.questions.length) {
    container.append(make("div", "empty", "No decision question passed grounding validation for this paper."));
    return;
  }
  state.paper.questions.forEach((item) => {
    const card = make("button", "card question-card");
    const top = make("div", "card-top");
    top.append(make("span", "badge", item.question_type));
    top.append(make("span", "page", item.pdf_page ? `PDF p. ${item.pdf_page}` : "XML evidence"));
    card.append(top, make("p", "", item.question));
    card.append(make("p", "card-detail", `Decision use: ${item.decision_use}`));
    card.addEventListener("click", () => {
      item.card = card;
      showEvidence(item, `${item.question_type} decision question`);
    });
    container.append(card);
  });
}

function renderPaper() {
  const { metadata } = state.paper;
  $("paperTitle").textContent = metadata.title || state.paper.paper_id;
  $("paperMeta").textContent = [
    state.paper.paper_id,
    metadata.journal,
    metadata.publication_year,
    metadata.doi ? `DOI ${metadata.doi}` : "",
  ].filter(Boolean).join(" · ");
  $("pdfNotice").textContent = state.paper.pdf_notice;
  $("roleCount").textContent = `(${state.paper.roles.length})`;
  $("questionCount").textContent = `(${state.paper.questions.length})`;
  $("pdfViewer").src = state.paper.pdf_url;
  $("openPdf").href = state.paper.pdf_url;
  $("pdfPageLabel").textContent = "PDF";
  $("evidenceDrawer").classList.remove("open");
  state.activeRole = "all";
  renderRoleFilters();
  renderRoles();
  renderQuestions();
}

async function loadPaper(paperId) {
  $("paperTitle").textContent = "Loading paper…";
  const response = await fetch(`/api/papers/${paperId}`);
  if (!response.ok) throw new Error(`Failed to load ${paperId}`);
  state.paper = await response.json();
  renderPaper();
}

function configureTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll('[role="tabpanel"]').forEach((panel) => panel.classList.add("hidden"));
      tab.classList.add("active");
      $(tab.dataset.panel).classList.remove("hidden");
      $("roleFilters").classList.toggle("hidden", tab.dataset.panel !== "rolesPanel");
    });
  });
}

async function initialize() {
  configureTabs();
  $("closeEvidence").addEventListener("click", () => $("evidenceDrawer").classList.remove("open"));
  const response = await fetch("/api/papers");
  if (!response.ok) throw new Error("Failed to load papers");
  state.papers = await response.json();
  const select = $("paperSelect");
  state.papers.forEach((paper) => {
    const option = document.createElement("option");
    option.value = paper.paper_id;
    option.textContent = `${paper.rank}. ${paper.title} · ${paper.role_count} roles · ${paper.question_count} questions`;
    select.append(option);
  });
  select.addEventListener("change", () => loadPaper(select.value));
  if (state.papers.length) await loadPaper(state.papers[0].paper_id);
}

initialize().catch((error) => {
  $("paperTitle").textContent = "Interface error";
  $("paperMeta").textContent = error.message;
});
