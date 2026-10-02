const state = {
  papers: [],
  paper: null,
  activeRoles: null,
  questionFilters: {
    search: "",
    type: "all",
    intent: "all",
    relevance: "all",
  },
  selectedItem: null,
  pdfPage: 1,
  pdfZoom: 1,
};

const $ = (id) => document.getElementById(id);

function make(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function pdfUrl(page = state.pdfPage) {
  return `${state.paper.pdf_url}#page=${page}`;
}

function matchForPage(item, page) {
  return item?.pdf_matches?.find((match) => match.page === page);
}

function renderPdfHighlights() {
  const layer = $("pdfHighlights");
  layer.replaceChildren();
  const match = matchForPage(state.selectedItem, state.pdfPage);
  if (!match) return;
  match.highlights.forEach((rectangle) => {
    const highlight = make("div", "pdf-highlight");
    highlight.style.left = `${(rectangle.x / match.page_width) * 100}%`;
    highlight.style.top = `${(rectangle.y / match.page_height) * 100}%`;
    highlight.style.width = `${(rectangle.width / match.page_width) * 100}%`;
    highlight.style.height = `${(rectangle.height / match.page_height) * 100}%`;
    highlight.title = `Evidence span ${rectangle.span_index + 1}`;
    layer.append(highlight);
  });
}

function renderPdfPage(page) {
  state.pdfPage = Math.min(Math.max(page, 1), state.paper.pdf_page_count);
  const evidencePages = state.selectedItem?.pdf_matches?.map((match) => match.page) || [];
  const currentMatch = matchForPage(state.selectedItem, state.pdfPage);
  $("pdfImage").src = `/api/papers/${state.paper.paper_id}/pdf/pages/${state.pdfPage}.png`;
  $("pdfImage").onload = renderPdfHighlights;
  $("pdfPage").style.width = `${state.pdfZoom * 100}%`;
  $("pagePosition").textContent = `${state.pdfPage} / ${state.paper.pdf_page_count}`;
  $("zoomLevel").textContent = `${Math.round(state.pdfZoom * 100)}%`;
  $("previousPage").disabled = state.pdfPage === 1;
  $("nextPage").disabled = state.pdfPage === state.paper.pdf_page_count;
  $("openPdf").href = pdfUrl();
  if (currentMatch) {
    const otherPages = evidencePages.length > 1 ? ` · evidence pages ${evidencePages.join(", ")}` : "";
    $("pdfPageLabel").textContent = `PDF · highlighted evidence on page ${state.pdfPage}${otherPages}`;
  } else if (state.selectedItem?.pdf_page === state.pdfPage) {
    $("pdfPageLabel").textContent = `PDF · approximate page ${state.pdfPage}; exact PDF text not found`;
  } else {
    const evidenceLabel = evidencePages.length ? ` · evidence pages ${evidencePages.join(", ")}` : "";
    $("pdfPageLabel").textContent = `PDF · page ${state.pdfPage}${evidenceLabel}`;
  }
  renderPdfHighlights();
}

function setPdfZoom(zoom) {
  state.pdfZoom = Math.min(Math.max(zoom, 0.6), 2);
  $("pdfPage").style.width = `${state.pdfZoom * 100}%`;
  $("zoomLevel").textContent = `${Math.round(state.pdfZoom * 100)}%`;
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
  state.selectedItem = item;
  if (item.pdf_page) {
    renderPdfPage(item.pdf_page);
  } else {
    renderPdfPage(state.pdfPage);
    $("pdfPageLabel").textContent = "PDF · page match unavailable";
  }
}

function renderRoleFilters() {
  const container = $("roleFilters");
  container.replaceChildren();
  container.append(make("span", "filter-label", "Filter roles"));
  const counts = state.paper.roles.reduce((result, item) => {
    result.set(item.role, (result.get(item.role) || 0) + 1);
    return result;
  }, new Map());
  const roles = [...counts.keys()].sort();
  const allButton = make(
    "button",
    `filter${state.activeRoles === null ? " active" : ""}`,
    `All roles (${state.paper.roles.length})`,
  );
  allButton.setAttribute("aria-pressed", String(state.activeRoles === null));
  allButton.addEventListener("click", () => {
    state.activeRoles = null;
    renderRoles();
    renderRoleFilters();
  });
  container.append(allButton);
  roles.forEach((role) => {
    const selected = state.activeRoles?.has(role) || false;
    const label = `${role.replaceAll("_", " ")} (${counts.get(role)})`;
    const button = make("button", `filter${selected ? " active" : ""}`, label);
    button.setAttribute("aria-pressed", String(selected));
    button.addEventListener("click", () => {
      if (state.activeRoles === null) {
        state.activeRoles = new Set([role]);
      } else if (state.activeRoles.has(role)) {
        state.activeRoles.delete(role);
      } else {
        state.activeRoles.add(role);
      }
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
    (item) => state.activeRoles === null || state.activeRoles.has(item.role),
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
    $("questionResultCount").textContent = "0 / 0";
    container.append(make("div", "empty", "No grounded reader question is available for this paper."));
    return;
  }
  const search = state.questionFilters.search.toLowerCase();
  const questions = state.paper.questions.filter((item) => (
    (state.questionFilters.type === "all" || item.question_type === state.questionFilters.type)
    && (state.questionFilters.intent === "all" || item.reader_intent === state.questionFilters.intent)
    && (state.questionFilters.relevance === "all" || item.relevance === state.questionFilters.relevance)
    && (!search || `${item.question} ${item.rationale || ""}`.toLowerCase().includes(search))
  ));
  $("questionResultCount").textContent = `${questions.length} / ${state.paper.questions.length}`;
  if (!questions.length) {
    container.append(make("div", "empty", "No questions match these filters."));
    return;
  }
  questions.forEach((item) => {
    const card = make("button", "card question-card");
    const top = make("div", "card-top");
    top.append(make("span", "badge", item.question_type));
    top.append(make("span", "page", item.pdf_page ? `PDF p. ${item.pdf_page}` : "XML evidence"));
    card.append(top, make("p", "", item.question));
    const detail = item.reader_intent
      ? [
          item.reading_step?.replaceAll("_", " "),
          item.reader_intent.replaceAll("_", " "),
          item.relevance,
          item.source_section || "source passage",
          item.rationale,
        ].filter(Boolean).join(" · ")
      : `Decision use: ${item.decision_use}`;
    card.append(make("p", "card-detail", detail));
    card.addEventListener("click", () => {
      item.card = card;
      showEvidence(
        item,
        `${item.question_type} ${item.reader_intent ? "reader" : "decision"} question`,
      );
    });
    container.append(card);
  });
}

function setSelectOptions(select, values, allLabel) {
  select.replaceChildren();
  const allOption = document.createElement("option");
  allOption.value = "all";
  allOption.textContent = allLabel;
  select.append(allOption);
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value.replaceAll("_", " ");
    select.append(option);
  });
}

function renderQuestionFilters() {
  const questions = state.paper.questions;
  setSelectOptions(
    $("questionTypeFilter"),
    [...new Set(questions.map((item) => item.question_type).filter(Boolean))].sort(),
    "All types",
  );
  setSelectOptions(
    $("questionIntentFilter"),
    [...new Set(questions.map((item) => item.reader_intent).filter(Boolean))].sort(),
    "All intents",
  );
  setSelectOptions(
    $("questionRelevanceFilter"),
    [...new Set(questions.map((item) => item.relevance).filter(Boolean))].sort(),
    "All relevance",
  );
  $("questionSearch").value = "";
  state.questionFilters = {search: "", type: "all", intent: "all", relevance: "all"};
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
  $("pdfPageLabel").textContent = "PDF";
  $("evidenceDrawer").classList.remove("open");
  state.selectedItem = null;
  state.pdfPage = 1;
  state.pdfZoom = 1;
  renderPdfPage(1);
  state.activeRoles = null;
  renderRoleFilters();
  renderRoles();
  renderQuestionFilters();
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
      $("questionFilters").classList.toggle("hidden", tab.dataset.panel !== "questionsPanel");
    });
  });
}

async function initialize() {
  configureTabs();
  $("closeEvidence").addEventListener("click", () => $("evidenceDrawer").classList.remove("open"));
  $("previousPage").addEventListener("click", () => renderPdfPage(state.pdfPage - 1));
  $("nextPage").addEventListener("click", () => renderPdfPage(state.pdfPage + 1));
  $("zoomOut").addEventListener("click", () => setPdfZoom(state.pdfZoom - 0.2));
  $("zoomIn").addEventListener("click", () => setPdfZoom(state.pdfZoom + 0.2));
  $("questionSearch").addEventListener("input", (event) => {
    state.questionFilters.search = event.target.value.trim();
    renderQuestions();
  });
  for (const [id, key] of [
    ["questionTypeFilter", "type"],
    ["questionIntentFilter", "intent"],
    ["questionRelevanceFilter", "relevance"],
  ]) {
    $(id).addEventListener("change", (event) => {
      state.questionFilters[key] = event.target.value;
      renderQuestions();
    });
  }
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
