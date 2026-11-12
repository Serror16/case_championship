const $ = (id) => document.getElementById(id);
const STORE = "chukotka-index-scenario-v1";
const seasonNames = ["Зима", "Весеннее межсезонье", "Лето", "Осеннее межсезонье"];
const state = { bootstrap: null, additions: [], removed: [], rows: null, baselineRows: null, displayedHorizon: 48, metric: "random_start", dirty: false, busy: false, revision: 0 };
const format = (value) => `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1, minimumFractionDigits: 1 }).format(value)}%`;
const horizonLabel = (hours) => Number.isInteger(hours) && hours >= 1 && hours <= 168 ? `${hours} ч` : "не задан";
const selectedHorizon = () => Number($("horizon").value);

function restore() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORE) || "{}");
    state.additions = Array.isArray(saved.additions) ? saved.additions : [];
    state.removed = Array.isArray(saved.removed) ? saved.removed : [];
  } catch { state.additions = []; state.removed = []; }
}
function persist() { sessionStorage.setItem(STORE, JSON.stringify({ additions: state.additions, removed: state.removed })); }
function option(value, label = value) { const el = document.createElement("option"); el.value = value; el.textContent = label; return el; }
function button(text, handler, className = "small-button") { const el = document.createElement("button"); el.type = "button"; el.className = className; el.textContent = text; el.addEventListener("click", handler); return el; }
function message(text, error = false) { const el = $("message"); el.textContent = text; el.classList.toggle("error", error); el.hidden = !text; }
function markDirty() {
  state.revision += 1;
  state.dirty = true;
  persist(); renderScenario(); renderCatalog(); renderStatus();
  message("Сценарий изменён. Нажмите «Пересчитать индекс», чтобы обновить таблицу.");
}

function renderStatus() {
  const count = state.additions.length + state.removed.length;
  const pending = state.dirty || selectedHorizon() !== state.displayedHorizon;
  $("result-status").textContent = pending
    ? `Показан предыдущий расчёт · H = ${horizonLabel(state.displayedHorizon)}. Выбран H = ${horizonLabel(selectedHorizon())} · нажмите «Пересчитать индекс»`
    : `${count ? "Сценарий" : "Исходная сеть"} · порог ${horizonLabel(state.displayedHorizon)}`;
  $("calculate").disabled = state.busy;
  $("calculate").textContent = state.busy ? "Выполняется расчёт…" : "Пересчитать индекс ↗";
}

function renderScenario() {
  const container = $("scenario-list"); container.replaceChildren();
  if (!state.additions.length && !state.removed.length) {
    const empty = document.createElement("p"); empty.className = "empty";
    empty.textContent = "Пока без изменений. Добавьте или исключите соединение, чтобы увидеть влияние на индекс.";
    container.append(empty);
  }
  state.additions.forEach((item, index) => {
    const row = document.createElement("div"); row.className = "change-row";
    const label = document.createElement("span");
    label.textContent = `＋ ${item.origin} → ${item.destination}${item.reverse ? " ↔" : ""} · ${item.first_date}–${item.last_date} · раз в ${item.repeat_days} дн.`;
    row.append(label, button("Убрать", () => { state.additions.splice(index, 1); markDirty(); })); container.append(row);
  });
  state.removed.forEach((id) => {
    const group = state.bootstrap.catalog.find((item) => item.id === id);
    if (!group) return;
    const row = document.createElement("div"); row.className = "change-row";
    const label = document.createElement("span"); label.textContent = `− ${group.origin} → ${group.destination} · ${group.service}`;
    row.append(label, button("Вернуть", () => { state.removed = state.removed.filter((key) => key !== id); markDirty(); })); container.append(row);
  });
  $("scenario-summary").textContent = `${state.additions.length} добавлено · ${state.removed.length} исключено. Изменения действуют только в этой вкладке.`;
  $("reset").disabled = !state.additions.length && !state.removed.length;
}

function renderCatalog() {
  const query = $("route-search").value.trim().toLocaleLowerCase("ru-RU");
  const userRoutes = state.additions.map((item, index) => ({ item, index })).filter(({ item }) =>
    !query || `${item.origin} ${item.destination} ${item.reverse ? "обратно" : ""} пользовательский маршрут`.toLocaleLowerCase("ru-RU").includes(query));
  const rows = state.bootstrap.catalog.filter((item) => !state.removed.includes(item.id)
    && (!query || `${item.origin} ${item.destination} ${item.service} ${item.mode}`.toLocaleLowerCase("ru-RU").includes(query)));
  const list = $("route-list"); list.replaceChildren();
  for (const { item, index } of userRoutes.slice(0, 30)) {
    const row = document.createElement("div"); row.className = "catalog-row user-route";
    const copy = document.createElement("div");
    const title = document.createElement("strong"); title.textContent = `${item.origin} ${item.reverse ? "↔" : "→"} ${item.destination}`;
    const detail = document.createElement("small"); detail.textContent = `Ваш маршрут · ${item.first_date}–${item.last_date} · раз в ${item.repeat_days} дн.`;
    copy.append(title, detail);
    row.append(copy, button("Убрать", () => { state.additions.splice(index, 1); markDirty(); }));
    list.append(row);
  }
  for (const item of rows.slice(0, Math.max(0, 30 - userRoutes.length))) {
    const row = document.createElement("div"); row.className = "catalog-row";
    const copy = document.createElement("div");
    const title = document.createElement("strong"); title.textContent = `${item.origin} → ${item.destination}`;
    const detail = document.createElement("small"); detail.textContent = `${item.service} · ${item.count} отправлений`;
    copy.append(title, detail);
    row.append(copy, button("Исключить", () => { state.removed.push(item.id); markDirty(); }));
    list.append(row);
  }
  const total = userRoutes.length + rows.length;
  if (!total) { const empty = document.createElement("p"); empty.className = "empty"; empty.textContent = "Соединения не найдены."; list.append(empty); }
  if (total > 30) { const note = document.createElement("p"); note.className = "hint"; note.textContent = `Показаны 30 из ${total}. Уточните поиск.`; list.append(note); }
}

function renderTable() {
  const body = $("results-body"); body.replaceChildren();
  const horizon = state.displayedHorizon;
  const baseline = state.baselineRows;
  state.rows.forEach((row, index) => {
    const tr = document.createElement("tr");
    const th = document.createElement("th"); th.scope = "row";
    const link = document.createElement("a"); link.className = "place-link";
    link.href = `/place?name=${encodeURIComponent(row.place)}&h=${encodeURIComponent(horizon)}`;
    link.textContent = `${row.place} ↗`; th.append(link); tr.append(th);
    seasonNames.forEach((season) => {
      const td = document.createElement("td");
      const value = row.seasons[season][state.metric];
      const original = baseline[index].seasons[season][state.metric];
      const score = document.createElement("strong"); score.textContent = format(value); td.append(score);
      const delta = Math.round((value - original) * 10) / 10;
      if (delta !== 0) { const note = document.createElement("small"); note.className = delta > 0 ? "delta positive" : "delta negative"; note.textContent = `${delta > 0 ? "+" : ""}${format(delta)}`; td.append(note); }
      tr.append(td);
    });
    body.append(tr);
  });
}

async function calculate() {
  if (state.busy) return;
  const horizon = selectedHorizon();
  if (!Number.isInteger(horizon) || horizon < 1 || horizon > 168) { message("Введите целое число часов от 1 до 168.", true); return; }
  const revision = state.revision;
  state.busy = true; renderStatus(); message("Считаем все дни четырёх сезонов. Это может занять несколько секунд.");
  try {
    const response = await fetch("/api/calculate", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ region: $("region").value, horizon_hours: horizon, removed: state.removed, additions: state.additions }) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Не удалось выполнить расчёт");
    if (revision !== state.revision) { message("Параметры изменились во время расчёта. Нажмите «Пересчитать индекс» ещё раз."); return; }
    state.rows = result.rows; state.baselineRows = result.baseline; state.displayedHorizon = horizon; state.dirty = false; renderTable();
    message(`Готово. В графе ${result.counts.scenario_events.toLocaleString("ru-RU")} дуг: добавлено ${result.counts.added_events}, исключено ${result.counts.removed_events}.`);
  } catch (error) { message(error.message, true); }
  finally { state.busy = false; renderStatus(); }
}

async function start() {
  restore();
  try {
    const response = await fetch("/api/bootstrap");
    if (!response.ok) throw new Error("Не удалось загрузить исходную сеть");
    state.bootstrap = await response.json();
    for (const node of state.bootstrap.nodes) { $("origin").append(option(node)); $("destination").append(option(node)); }
    $("origin").value = "Анадырь"; $("destination").value = "Билибино";
    state.removed = state.removed.filter((id) => state.bootstrap.catalog.some((item) => item.id === id));
    state.displayedHorizon = 48;
    state.rows = state.bootstrap.baseline["48ч"];
    state.baselineRows = state.rows;
    state.dirty = Boolean(state.removed.length || state.additions.length);
    renderScenario(); renderCatalog(); renderTable(); renderStatus();
    if (state.dirty) message("Сценарий восстановлен из этой вкладки. Пересчитайте индекс.");
    $("route-form").addEventListener("submit", (event) => {
      event.preventDefault();
      const item = { origin: $("origin").value, destination: $("destination").value,
        first_date: $("first-date").value, last_date: $("last-date").value,
        departure_time: $("departure-time").value, duration_minutes: Number($("duration").value),
        repeat_days: Number($("repeat-days").value), reverse: $("reverse").checked };
      if (item.origin === item.destination || item.first_date > item.last_date) { message("Проверьте пункты и диапазон дат.", true); return; }
      if (state.additions.length >= 30) { message("Можно добавить не более 30 соединений.", true); return; }
      state.additions.push(item); markDirty();
    });
    $("route-search").addEventListener("input", renderCatalog);
    $("calculate").addEventListener("click", calculate);
    $("reset").addEventListener("click", () => { state.revision += 1; state.additions = []; state.removed = []; state.rows = state.baselineRows; state.dirty = false; persist(); renderScenario(); renderCatalog(); renderTable(); renderStatus(); message("Исходная сеть восстановлена. Для выбранного H нажмите «Пересчитать индекс»."); });
    $("horizon").addEventListener("input", () => { state.revision += 1; renderStatus(); message(selectedHorizon() === state.displayedHorizon && !state.dirty ? "" : "Порог H задан. Нажмите «Пересчитать индекс», чтобы обновить таблицу."); });
    document.querySelectorAll("[data-metric]").forEach((button) => button.addEventListener("click", () => {
      state.metric = button.dataset.metric;
      document.querySelectorAll("[data-metric]").forEach((item) => item.classList.toggle("active", item === button));
      renderTable();
    }));
  } catch (error) { message(error.message, true); }
}
start();
