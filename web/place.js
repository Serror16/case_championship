const $ = (id) => document.getElementById(id);
const STORE = "chukotka-index-scenario-v1";
const seasons = ["Зима", "Весеннее межсезонье", "Лето", "Осеннее межсезонье"];
const params = new URLSearchParams(location.search);
const place = params.get("name") || "";
const state = { current: null, baseline: null, season: "Зима", displayedHorizon: 48, busy: false, revision: 0 };
const percent = (value) => `${new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(value)}%`;

function scenario() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORE) || "{}");
    return { additions: Array.isArray(saved.additions) ? saved.additions : [],
      removed: Array.isArray(saved.removed) ? saved.removed : [] };
  } catch { return { additions: [], removed: [] }; }
}

function message(text, error = false) {
  const box = $("detail-message");
  box.textContent = text;
  box.classList.toggle("error", error);
  box.hidden = !text;
}

function scoreCell(value, baseline) {
  const box = document.createElement("span");
  const score = document.createElement("strong"); score.textContent = percent(value); box.append(score);
  const difference = Math.round((value - baseline) * 10) / 10;
  if (difference) {
    const delta = document.createElement("small");
    delta.className = difference > 0 ? "delta positive" : "delta negative";
    delta.textContent = `${difference > 0 ? "+" : ""}${percent(difference)}`;
    box.append(delta);
  }
  return box;
}

function renderCards() {
  const container = $("season-cards"); container.replaceChildren();
  for (const season of seasons) {
    const current = state.current.seasons[season];
    const baseline = state.baseline.seasons[season];
    const card = document.createElement("button"); card.type = "button";
    card.className = `season-card ${state.season === season ? "active" : ""}`;
    const heading = document.createElement("span"); heading.className = "season-card-title"; heading.textContent = season;
    const main = document.createElement("span"); main.className = "season-card-value";
    main.append(scoreCell(current.random_start_pct, baseline.random_start_pct));
    const secondary = document.createElement("span"); secondary.className = "season-card-secondary";
    secondary.textContent = `Достижимо хотя бы раз: ${percent(current.ever_reachable_pct)}`;
    card.append(heading, main, secondary);
    card.addEventListener("click", () => { state.season = season; renderCards(); renderRows(); });
    container.append(card);
  }
}

function statusLabel(row) {
  if (row.diagnosis === "no_path_7d") return "Связь не найдена";
  if (row.diagnosis === "over_h") return "Связь найдена, за пределами H";
  return "Связь в пределах H найдена";
}

function sortDestinations(rows) {
  const diagnosisOrder = { reachable: 0, over_h: 1, no_path_7d: 2 };
  return rows.sort((a, b) => b.successful_starts - a.successful_starts
    || diagnosisOrder[a.diagnosis] - diagnosisOrder[b.diagnosis]
    || a.destination.localeCompare(b.destination, "ru"));
}

async function showJourney(row, tableRow) {
  const expanded = document.createElement("tr"); expanded.className = "journey-row";
  const cell = document.createElement("td"); cell.colSpan = 5;
  cell.textContent = "Загружаем цепочку поездки…";
  expanded.append(cell); tableRow.after(expanded);
  try {
    const response = await fetch("/api/journey", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ region: "Чукотка", place, destination: row.destination,
        start: row.fastest_start, horizon_hours: state.displayedHorizon, ...scenario() }),
    });
    const journey = await response.json();
    if (!response.ok) throw new Error(journey.error || "Не удалось загрузить поездку");
    cell.replaceChildren();
    if (!journey.found) { cell.textContent = "Цепочка поездки не найдена в текущем сценарии."; return; }
    const title = document.createElement("strong"); title.textContent = `Пример самой быстрой поездки: ${journey.total_hours} ч от начала пути`;
    const list = document.createElement("ol"); list.className = "journey-legs";
    for (const leg of journey.legs) {
      const item = document.createElement("li");
      const route = document.createElement("strong"); route.textContent = `${leg.origin} → ${leg.destination}`;
      const details = document.createElement("span");
      details.textContent = ` · ${leg.service} · ${leg.departure.slice(0, 16).replace("T", " ")} — ${leg.arrival.slice(0, 16).replace("T", " ")}`;
      item.append(route, details);
      if (leg.assumption) { const note = document.createElement("small"); note.textContent = `Допущение: ${leg.assumption}`; item.append(note); }
      if (leg.source?.startsWith("https://")) {
        const source = document.createElement("a"); source.href = leg.source;
        source.target = "_blank"; source.rel = "noopener noreferrer";
        source.textContent = "Источник ↗"; item.append(source);
      }
      list.append(item);
    }
    cell.append(title, list);
  } catch (error) { cell.textContent = error.message; }
}

function renderRows() {
  $("season-title").textContent = state.season;
  const current = state.current.seasons[state.season].destinations;
  const baseline = new Map(state.baseline.seasons[state.season].destinations.map((row) => [row.destination, row]));
  const filter = $("destination-filter").value;
  const shown = current.filter((row) => filter === "all" || row.diagnosis === filter);
  sortDestinations(shown);
  const body = $("destination-body"); body.replaceChildren();
  for (const row of shown) {
    const tr = document.createElement("tr");
    const th = document.createElement("th"); th.scope = "row"; th.textContent = row.destination; tr.append(th);
    const probability = document.createElement("td");
    probability.append(scoreCell(row.random_start_pct, baseline.get(row.destination).random_start_pct)); tr.append(probability);
    const ever = document.createElement("td"); ever.textContent = row.ever_reachable ? "Да" : "Нет"; tr.append(ever);
    const fastest = document.createElement("td");
    if (row.fastest_known_hours === null) fastest.textContent = "—";
    else {
      const duration = document.createElement("span");
      duration.textContent = `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(row.fastest_known_hours)} ч `;
      const path = document.createElement("button"); path.type = "button"; path.className = "text-button"; path.textContent = "Путь ↗";
      path.addEventListener("click", () => {
        const next = tr.nextElementSibling;
        if (next?.classList.contains("journey-row")) next.remove();
        else showJourney(row, tr);
      });
      fastest.append(duration, path);
    }
    tr.append(fastest);
    const statusCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `connection-badge ${row.diagnosis}`;
    badge.textContent = statusLabel(row);
    statusCell.append(badge); tr.append(statusCell);
    body.append(tr);
  }
  $("detail-count").textContent = `Показано ${shown.length} из ${current.length} направлений · ${state.current.seasons[state.season].checked_starts} моментов старта проверено в сезоне.`;
}

async function load() {
  if (state.busy) return;
  const horizon = Number($("horizon").value);
  if (!Number.isInteger(horizon) || horizon < 1 || horizon > 168) {
    message("Введите целое число часов от 1 до 168.", true); return;
  }
  const revision = ++state.revision;
  state.busy = true; $("refresh").disabled = true; $("horizon").disabled = true;
  message("Считаем поездки из выбранного пункта по всем дням 2026 года…");
  try {
    const edits = scenario();
    const response = await fetch("/api/place", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ region: "Чукотка", place, horizon_hours: horizon, ...edits }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Не удалось получить подробности");
    if (revision !== state.revision) return;
    state.current = result.current; state.baseline = result.baseline; state.displayedHorizon = horizon;
    const overHOption = $("destination-filter").querySelector('option[value="over_h"]');
    overHOption.disabled = horizon === 168;
    if (overHOption.disabled && $("destination-filter").value === "over_h") $("destination-filter").value = "all";
    renderCards(); renderRows();
    const changed = edits.additions.length + edits.removed.length;
    message(changed ? `Показан ваш сценарий: ${edits.additions.length} добавлено, ${edits.removed.length} исключено. H = ${horizon} ч.`
      : `Показана исходная сеть. H = ${horizon} ч.`);
  } catch (error) { message(error.message, true); }
  finally { state.busy = false; $("refresh").disabled = false; $("horizon").disabled = false; }
}

$("place-title").textContent = place || "Пункт не выбран";
document.title = `${place || "Населённый пункт"} · Индекс транспортной достижимости`;
const queryHorizon = ({ "48ч": 48, "72ч": 72, "7сут": 168 })[params.get("h")] ?? Number(params.get("h"));
if (Number.isInteger(queryHorizon) && queryHorizon >= 1 && queryHorizon <= 168) $("horizon").value = queryHorizon;
$("refresh").addEventListener("click", load);
$("destination-filter").addEventListener("change", () => { if (state.current) renderRows(); });
$("horizon").addEventListener("input", () => {
  if (state.current) message("Выбран другой порог H. Нажмите «Рассчитать подробности», чтобы обновить таблицу.");
});
load();
