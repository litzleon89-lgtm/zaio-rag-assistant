const form = document.querySelector("#ask-form");
const input = document.querySelector("#question");
const sendButton = document.querySelector("#send-button");
const messages = document.querySelector("#messages");
const welcome = document.querySelector("#welcome");
const statusDot = document.querySelector("#status-dot");
const statusLabel = document.querySelector("#status-label");
const chunkCount = document.querySelector("#chunk-count");
const refusal = "I could not find that information in the available knowledge base.";

function setStatus(online, count = null) {
  statusDot.classList.toggle("online", online);
  statusDot.classList.toggle("offline", !online);
  statusLabel.textContent = online ? "Connected" : "API offline";
  chunkCount.textContent = count === null ? "--" : `${count} chunks`;
}

async function refreshHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) throw new Error("health check failed");
    const health = await response.json();
    setStatus(health.status === "ok", health.indexed_chunks);
  } catch {
    setStatus(false);
  }
}

function makeMessage(className, text) {
  const element = document.createElement("div");
  element.className = className;
  element.textContent = text;
  return element;
}

function showAnswer(answer, source) {
  const block = document.createElement("article");
  block.className = "message answer-block";

  const label = document.createElement("div");
  label.className = "answer-label";
  const mark = document.createElement("span");
  mark.className = "answer-label-mark";
  mark.textContent = "Z";
  const labelText = document.createElement("span");
  labelText.textContent = "ZAIO KNOWLEDGE DESK";
  label.append(mark, labelText);

  const answerText = document.createElement("div");
  answerText.className = "answer-text";
  answerText.textContent = answer;
  block.append(label, answerText);

  if (answer.length > 850) {
    answerText.classList.add("collapsed");
    const expandButton = document.createElement("button");
    expandButton.className = "expand-answer";
    expandButton.type = "button";
    expandButton.textContent = "Read full answer";
    expandButton.setAttribute("aria-expanded", "false");
    expandButton.addEventListener("click", () => {
      const expanded = answerText.classList.toggle("collapsed") === false;
      expandButton.textContent = expanded ? "Show less" : "Read full answer";
      expandButton.setAttribute("aria-expanded", String(expanded));
    });
    block.append(expandButton);
  }

  if (source) {
    const citation = document.createElement("a");
    citation.className = "citation";
    citationText(citation, source);
    block.append(citation);
  } else {
    const citation = document.createElement("div");
    citation.className = "citation empty";
    citationText(citation, "No matching source");
    block.append(citation);
  }

  messages.append(block);
  block.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function citationText(container, source) {
  const mark = document.createElement("span");
  mark.className = "citation-mark";
  mark.textContent = source.startsWith("http") ? "↗" : "p";
  const text = document.createElement("span");
  text.textContent = source;
  container.append(mark, text);
  if (container.tagName === "A" && source.startsWith("http")) {
    container.href = source;
    container.target = "_blank";
    container.rel = "noopener noreferrer";
  } else if (container.tagName === "A") {
    container.removeAttribute("href");
    container.setAttribute("role", "note");
  }
}

async function ask(question) {
  const normalized = question.trim();
  if (!normalized || sendButton.disabled) return;
  welcome.hidden = true;
  messages.append(makeMessage("message message-question", normalized));
  const pending = makeMessage("message thinking", "Searching both sources");
  messages.append(pending);
  sendButton.disabled = true;
  input.disabled = true;
  input.value = "";
  input.style.height = "auto";

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: normalized }),
    });
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    const result = await response.json();
    pending.remove();
    showAnswer(result.answer || refusal, result.source || null);
  } catch (error) {
    pending.remove();
    showAnswer(`Could not reach the assistant. ${error.message}`, null);
    setStatus(false);
  } finally {
    sendButton.disabled = false;
    input.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  ask(input.value);
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 132)}px`;
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

document.querySelectorAll(".prompt").forEach((prompt) => {
  prompt.addEventListener("click", () => ask(prompt.dataset.question));
});

refreshHealth();