(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const START = Date.UTC(2026, 7, 1, 0, 0, 0);
  const HORIZON = 6 * 86400;
  const COLORS = ["#315efb", "#12b76a", "#f79009", "#7a5af8", "#f04438"];
  let catalog = null;
  let activePlan = null;
  let selectedStation = 1;
  let weather = [];
  let currentViolations = [];
  let acceptancePage = 0;
  const uploadedPlans = new Map();

  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const fmt = (n, digits = 1) => Number(n || 0).toLocaleString("zh-CN", {maximumFractionDigits: digits, minimumFractionDigits: digits});
  const timeUTC = (seconds) => new Date(START + Number(seconds) * 1000).toISOString().replace(".000Z", "Z");
  const dateLabel = (seconds) => timeUTC(seconds).replace("T", " ").slice(0, 16) + " UTC";
  const pct = (value) => `${(100 * Number(value || 0)).toFixed(2)}%`;
  const tasks = () => activePlan?.tasks || [];

  async function jsonFetch(url, options) {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    return data;
  }

  function fillPlanSelect(select) {
    select.innerHTML = catalog.plans.map((p) => `<option value="${esc(p.id)}">${esc(p.label)}</option>`).join("");
  }

  async function loadPlan(id) {
    const data = await jsonFetch(`/api/dashboard/plan/${encodeURIComponent(id)}`);
    activePlan = data;
    currentViolations = data.violations || [];
    uploadedPlans.set(data.id, data);
    $("dashboardSourceStatus").textContent = `${data.label} · ${data.tasks.length.toLocaleString()}项 · ${data.sha256.slice(0, 12)}…`;
    $("dashboardSourceStatus").className = `pill ${data.metrics?.legal ? "status-pass" : "status-warn"}`;
    renderAll();
  }

  async function importPlan(file) {
    if (!file) return;
    if (file.size > 20 * 1024 * 1024) throw new Error("排程CSV最大20 MB");
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error("读取排程文件失败"));
      reader.onload = () => resolve(reader.result);
      reader.readAsDataURL(file);
    });
    $("dashboardSourceStatus").textContent = "正在运行独立裁判…";
    $("dashboardSourceStatus").className = "pill status-warn";
    const data = await jsonFetch("/api/dashboard/inspect", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({name: file.name, schedule_base64: String(dataUrl).split(",")[1]})
    });
    activePlan = data;
    currentViolations = data.violations || [];
    const select = $("sharedPlan");
    const value = `uploaded:${data.id}`;
    let option = [...select.options].find((item) => item.value === value);
    if (!option) {
      option = document.createElement("option");
      option.value = value;
      option.textContent = `${data.label}（本次验收）`;
      select.append(option);
    }
    select.value = value;
    $("dashboardSourceStatus").textContent = `${data.label} · ${data.metrics.violation_count}项违规 · ${data.sha256.slice(0, 12)}…`;
    $("dashboardSourceStatus").className = `pill ${data.metrics.legal ? "status-pass" : "status-fail"}`;
    renderAll();
  }

  function stationTasks(stationId) {
    return tasks().filter((task) => Number(task.station_id) === Number(stationId))
      .sort((a, b) => a.start_s - b.start_s || a.end_s - b.end_s);
  }

  function priorityClass(value) {
    const p = String(value || "").toLowerCase();
    return p === "high" || p === "高" ? "high" : p === "medium" || p === "中" ? "medium" : p === "low" || p === "低" ? "low" : "unknown";
  }

  function loadColor(ratio) {
    const low = [18, 183, 106], high = [240, 68, 56];
    const t = Math.max(0, Math.min(1, ratio));
    const rgb = low.map((value, i) => Math.round(value * (1 - t) + high[i] * t));
    return `rgb(${rgb.join(",")})`;
  }

  function renderMap() {
    if (!catalog || !activePlan) return;
    const svg = $("stationMapSvg");
    svg.replaceChildren();
    const NS = "http://www.w3.org/2000/svg";
    const add = (name, attrs = {}, text = "") => {
      const node = document.createElementNS(NS, name);
      Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
      if (text) node.textContent = text;
      svg.append(node);
      return node;
    };
    for (let lon = -180; lon <= 180; lon += 30) {
      const x = (lon + 180) / 360 * 1000;
      add("line", {x1:x, y1:0, x2:x, y2:500, class:"map-grid"});
      if (lon < 180) add("text", {x:x + 3, y:493, class:"map-label"}, `${lon}°`);
    }
    for (let lat = -60; lat <= 60; lat += 30) {
      const y = (90 - lat) / 180 * 500;
      add("line", {x1:0, y1:y, x2:1000, y2:y, class:"map-grid"});
      add("text", {x:4, y:y - 4, class:"map-label"}, `${lat}°`);
    }
    const counts = Object.fromEntries(catalog.stations.map((site) => [site.station_id, stationTasks(site.station_id).length]));
    const maxCount = Math.max(1, ...Object.values(counts));
    catalog.stations.forEach((site) => {
      let lon = site.longitude_deg > 180 ? site.longitude_deg - 360 : site.longitude_deg;
      const x = (lon + 180) / 360 * 1000;
      const y = (90 - site.latitude_deg) / 180 * 500;
      const ratio = counts[site.station_id] / maxCount;
      const radius = 7 + 7 * ratio;
      const dot = add("circle", {cx:x, cy:y, r:radius, fill:loadColor(ratio), class:`station-marker${site.station_id === selectedStation ? " selected" : ""}`, tabindex:0, role:"button", "aria-label":`站点${site.station_id}，${counts[site.station_id]}项任务`});
      const title = document.createElementNS(NS, "title"); title.textContent = `站点${site.station_id} · ${counts[site.station_id]}项任务`; dot.append(title);
      const labelX = x > 840 ? x - 30 : x + 12;
      add("text", {x:labelX, y:y - 10, class:"station-tag"}, String(site.station_id));
      dot.addEventListener("click", () => { selectedStation = site.station_id; renderMap(); renderStationDetails(); });
      dot.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { selectedStation = site.station_id; renderMap(); renderStationDetails(); } });
    });
    $("mapLegend").innerHTML = `<span class="legend-item"><i class="legend-dot" style="background:${loadColor(0)}"></i>任务较少</span><span class="legend-item"><i class="legend-dot" style="background:${loadColor(.5)}"></i>中等负载</span><span class="legend-item"><i class="legend-dot" style="background:${loadColor(1)}"></i>任务较多</span><span class="legend-item">站点数量：${catalog.stations.length}</span>`;
    $("stationPlanStatus").textContent = `${activePlan.label} · ${tasks().length.toLocaleString()}项任务`;
  }

  function renderStationDetails() {
    if (!catalog || !activePlan) return;
    const site = catalog.stations.find((item) => item.station_id === selectedStation);
    const list = stationTasks(selectedStation);
    const seconds = list.reduce((sum, item) => sum + item.duration_s, 0);
    $("stationDetailTitle").textContent = `站点 ${selectedStation} 观测序列`;
    $("stationDetailMetrics").innerHTML = [
      ["经度", `${site.longitude_deg.toFixed(4)}°`], ["纬度", `${site.latitude_deg.toFixed(4)}°`],
      ["任务数", list.length.toLocaleString()], ["计划观测", `${fmt(seconds / 3600, 2)} 小时`]
    ].map(([label, value]) => `<div class="metric-chip"><span>${label}</span><b>${value}</b></div>`).join("");
    $("stationTaskRows").innerHTML = list.map((task) => `<tr><td>${esc(timeUTC(task.start_s))}</td><td>${esc(task.target_id)}</td><td>${fmt(task.duration_s, 1)}</td><td>${esc(task.priority)}</td></tr>`).join("") || `<tr><td colspan="4">此方案在该站没有任务。</td></tr>`;
  }

  function initTimeControls() {
    const start = $("timelineStart");
    for (let i = 0; i < 12; i++) {
      const seconds = i * 12 * 3600;
      const option = document.createElement("option");
      option.value = String(seconds);
      option.textContent = dateLabel(seconds);
      start.append(option);
    }
    const station = $("timelineStation");
    catalog.stations.forEach((site) => {
      const option = document.createElement("option"); option.value = String(site.station_id); option.textContent = `站点 ${site.station_id}`; station.append(option);
    });
  }

  function renderTimeline() {
    if (!activePlan || !catalog) return;
    const windowStart = Number($("timelineStart").value || 0);
    const widthHours = Number($("timelineHours").value || 12);
    const windowEnd = Math.min(HORIZON, windowStart + widthHours * 3600);
    const span = Math.max(1, windowEnd - windowStart);
    const stationFilter = $("timelineStation").value;
    const sites = catalog.stations.filter((site) => !stationFilter || String(site.station_id) === stationFilter);
    const tickStep = widthHours <= 1 ? 0.25 : widthHours <= 6 ? 1 : widthHours <= 12 ? 2 : widthHours <= 24 ? 4 : 24;
    const ticks = [];
    for (let h = 0; h <= widthHours + 0.001; h += tickStep) ticks.push(h);
    $("timelineAxis").innerHTML = ticks.map((h) => `<span class="axis-tick" style="left:${(h / widthHours) * 100}%">${h === 0 ? dateLabel(windowStart) : `+${h}h`}</span>`).join("");
    const allVisible = tasks().filter((task) => task.end_s > windowStart && task.start_s < windowEnd && (!stationFilter || String(task.station_id) === stationFilter));
    const siteTaskMap = new Map();
    allVisible.forEach((task) => { if (!siteTaskMap.has(task.station_id)) siteTaskMap.set(task.station_id, []); siteTaskMap.get(task.station_id).push(task); });
    $("timelineChart").innerHTML = sites.map((site) => {
      const entries = (siteTaskMap.get(site.station_id) || []).map((task) => {
        const leftSeconds = Math.max(task.start_s, windowStart);
        const rightSeconds = Math.min(task.end_s, windowEnd);
        const left = (leftSeconds - windowStart) / span * 100;
        const width = (rightSeconds - leftSeconds) / span * 100;
        const title = `站点${site.station_id} · 目标${task.target_id} · ${timeUTC(task.start_s)} – ${timeUTC(task.end_s)} · ${task.duration_s.toFixed(1)}秒`;
        return `<span class="task-block ${priorityClass(task.priority)}" style="left:${left}%;width:${width}%" title="${esc(title)}" aria-label="${esc(title)}"></span>`;
      }).join("");
      return `<div class="station-lane"><div class="lane-label">站点 ${site.station_id}</div><div class="lane-track">${entries}</div></div>`;
    }).join("");
    const sorted = allVisible.slice().sort((a, b) => a.station_id - b.station_id || a.start_s - b.start_s);
    const previous = new Map();
    const detailRows = sorted.slice(0, 3000).map((task) => {
      const priorEnd = previous.get(task.station_id);
      const gap = priorEnd === undefined ? "—" : fmt(task.start_s - priorEnd, 3);
      previous.set(task.station_id, task.end_s);
      return `<tr><td>${task.station_id}</td><td>${esc(timeUTC(task.start_s))}</td><td>${esc(timeUTC(task.end_s))}</td><td>${esc(task.target_id)}</td><td>${fmt(task.duration_s, 3)}</td><td>${gap}</td><td>${esc(task.priority)}</td></tr>`;
    });
    $("timelineTaskRows").innerHTML = detailRows.join("") || `<tr><td colspan="7">所选时间范围内没有任务。</td></tr>`;
    $("timelineCount").textContent = `显示 ${allVisible.length.toLocaleString()} 项任务（表格最多列出3,000项）。时间范围：${timeUTC(windowStart)} 至 ${timeUTC(windowEnd)}。颜色：高/中/低优先级。`;
  }

  function metricsOf(plan) {
    const m = plan.metrics || {};
    return {
      legal: !!m.legal, violation_count: Number(m.violation_count || 0),
      covered: Number(m.unique_covered_targets || 0), coverage: Number(m.coverage_rate || 0),
      score: Number(m.total_score || 0), tasks: Number(m.task_count ?? plan.tasks?.length ?? 0),
      repeats: Number(m.repeated_observation_count || 0), util: Number(m.overall_station_utilization || 0),
      priority: m.priority_metrics || {}, stations: m.station_metrics || {}
    };
  }

  function renderComparison() {
    if (!catalog || !activePlan) return;
    const plans = catalog.plans.map((item) => ({...item, metrics:item.metrics, tasks:null}));
    if (!plans.some((item) => item.id === activePlan.id)) plans.push(activePlan);
    const data = plans.map((plan, index) => ({plan, m:metricsOf(plan), color:COLORS[index % COLORS.length]}));
    const minX = Math.min(0, ...data.map((x) => x.m.covered));
    const maxX = Math.max(100, ...data.map((x) => x.m.covered));
    const minY = Math.min(0, ...data.map((x) => x.m.score));
    const maxY = Math.max(1, ...data.map((x) => x.m.score));
    const padX = (maxX - minX) * .06 || 1, padY = (maxY - minY) * .08 || 1;
    const x0=75, x1=675, y0=330, y1=35;
    const sx = (x) => x0 + (x - minX + padX) / (maxX - minX + 2 * padX) * (x1 - x0);
    const sy = (y) => y0 - (y - minY + padY) / (maxY - minY + 2 * padY) * (y0 - y1);
    const chart = $("paretoChart");
    const xTicks = 5, yTicks = 5;
    let svg = "";
    for (let i = 0; i <= xTicks; i++) {
      const value = minX + (maxX - minX) * i / xTicks;
      const x = sx(value);
      svg += `<line class="chart-grid" x1="${x}" y1="${y1}" x2="${x}" y2="${y0}"/><text class="chart-text" x="${x}" y="${y0+22}" text-anchor="middle">${Math.round(value).toLocaleString()}</text>`;
    }
    for (let i = 0; i <= yTicks; i++) {
      const value = minY + (maxY - minY) * i / yTicks;
      const y = sy(value);
      svg += `<line class="chart-grid" x1="${x0}" y1="${y}" x2="${x1}" y2="${y}"/><text class="chart-text" x="${x0-8}" y="${y+4}" text-anchor="end">${Math.round(value).toLocaleString()}</text>`;
    }
    svg += `<line class="chart-axis" x1="${x0}" y1="${y0}" x2="${x1}" y2="${y0}"/><line class="chart-axis" x1="${x0}" y1="${y1}" x2="${x0}" y2="${y0}"/><text class="chart-text" x="${(x0+x1)/2}" y="376" text-anchor="middle">独立覆盖目标数</text><text class="chart-text" transform="translate(18 ${(y0+y1)/2}) rotate(-90)" text-anchor="middle">原始总得分</text>`;
    data.forEach(({plan,m,color}, index) => {
      const dominated = data.some((other) => other !== data[index] && other.m.covered >= m.covered && other.m.score >= m.score && (other.m.covered > m.covered || other.m.score > m.score));
      svg += `<circle class="pareto-dot" cx="${sx(m.covered)}" cy="${sy(m.score)}" r="8" fill="${color}"><title>${esc(plan.label)} · ${m.covered}覆盖 · ${m.score.toFixed(3)}分 · ${dominated?"被支配":"非支配"}</title></circle>`;
    });
    chart.innerHTML = svg;
    $("paretoLegend").innerHTML = data.map(({plan,m,color}) => `<span class="legend-item"><i class="legend-dot" style="background:${color}"></i>${esc(plan.label)} · ${m.covered.toLocaleString()} / ${m.score.toFixed(1)}${m.legal ? " · 裁判通过" : " · 未通过"}</span>`).join("");
    $("comparisonRows").innerHTML = data.map(({plan,m}) => {
      const p = m.priority;
      const rates = ["high","medium","low"].map((k) => p[k] ? pct(p[k].coverage_rate) : "—").join(" / ");
      return `<tr class="${plan.id === activePlan.id ? "comparison-row current" : ""}"><td>${esc(plan.label)}</td><td>${m.legal ? "通过" : `违规${m.violation_count}`}</td><td>${m.covered.toLocaleString()}</td><td>${pct(m.coverage)}</td><td>${m.score.toFixed(3)}</td><td>${m.tasks.toLocaleString()} / ${m.repeats.toLocaleString()}</td><td>${rates}</td><td>${pct(m.util)}</td></tr>`;
    }).join("");
    const maxSite = Math.max(0, ...data.flatMap(({m}) => Object.values(m.stations).map((x) => Number(x.planning_horizon_utilization || 0))));
    $("stationUtilizationCompare").innerHTML = data.flatMap(({plan,m,color}) => Object.entries(m.stations).map(([site,metrics]) => {
      const value = Number(metrics.planning_horizon_utilization || 0);
      return `<div class="util-item"><b>${esc(plan.label)} · 站点${site}</b><span> ${pct(value)} · ${Number(metrics.task_count || 0).toLocaleString()}项</span><div class="util-track"><div class="util-fill" style="width:${maxSite ? Math.min(100,100*value/maxSite) : 0}%;background:${color}"></div></div></div>`;
    })).join("");
  }

  function renderAcceptance() {
    if (!activePlan) return;
    const m = metricsOf(activePlan);
    const violations = currentViolations || [];
    const byTask = new Map();
    violations.forEach((item) => {
      const key = item.task_id || "";
      if (!byTask.has(key)) byTask.set(key, []);
      byTask.get(key).push(item);
    });
    $("acceptanceBadge").textContent = m.legal ? "独立裁判通过" : `独立裁判发现 ${m.violation_count} 项问题`;
    $("acceptanceBadge").className = `pill ${m.legal ? "status-pass" : "status-fail"}`;
    const cards = [["裁判状态",m.legal?"通过":"未通过"],["违规项",m.violation_count],["任务数",m.tasks.toLocaleString()],["覆盖目标",m.covered.toLocaleString()],["原始得分",m.score.toFixed(3)],["方案SHA-256",activePlan.sha256.slice(0,12)+"…"]];
    $("acceptanceSummary").innerHTML = cards.map(([label,value]) => `<div class="card"><span>${esc(label)}</span><b>${esc(value)}</b></div>`).join("");
    const sourceNote = activePlan.validation_source === "recorded_referee_summary" ? "此结果来自材料包中冻结的Referee摘要；网页未在本次会话重新运行裁判。" : activePlan.validation_source === "independent_referee_this_session" ? "已在本次会话使用当前D缓存和独立Referee重新验收。" : "来自本机网页调度任务的独立Referee结果。";
    $("acceptanceMessage").textContent = sourceNote + (m.legal ? " 当前方案没有裁判违规。" : " 下表列出有具体任务ID的违规；全局类问题以明细说明为准。");
    const query = $("acceptanceSearch").value.trim().toLowerCase();
    const filtered = tasks().filter((task) => {
      const issueText = (byTask.get(task.task_id) || []).map((item) => `${item.category} ${item.detail}`).join(" ");
      return !query || `${task.task_id} ${task.target_id} ${task.station_id} ${issueText}`.toLowerCase().includes(query);
    }).sort((a,b) => Number(byTask.has(b.task_id)) - Number(byTask.has(a.task_id)) || a.start_s - b.start_s);
    const pageSize = Number($("acceptancePageSize").value || 100);
    const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
    acceptancePage = Math.max(0, Math.min(acceptancePage, pageCount - 1));
    const pageRows = filtered.slice(acceptancePage * pageSize, (acceptancePage + 1) * pageSize);
    const rows = pageRows.map((task) => {
      const issues = byTask.get(task.task_id) || [];
      const status = issues.length ? issues.map((item) => `${item.category}: ${item.detail}`).join("；") : m.legal ? "通过（整份排程零违规）" : "未定位到任务级原因";
      return `<tr><td>${esc(task.task_id)}</td><td>${esc(task.target_id)}</td><td>${task.station_id}</td><td>${esc(timeUTC(task.start_s))}</td><td>${esc(timeUTC(task.end_s))}</td><td>${fmt(task.duration_s,3)}</td><td>${esc(status)}</td></tr>`;
    });
    $("acceptanceRows").innerHTML = rows.join("") || `<tr><td colspan="7">没有可展示的任务。</td></tr>`;
    $("acceptanceCount").textContent = `筛选后 ${filtered.length.toLocaleString()} 项 / 共 ${tasks().length.toLocaleString()} 项；第 ${acceptancePage+1} / ${pageCount} 页；裁判违规明细 ${violations.length.toLocaleString()} 条。`;
    $("acceptancePrev").disabled = acceptancePage <= 0;
    $("acceptanceNext").disabled = acceptancePage >= pageCount - 1;
    $("downloadViolations").disabled = violations.length === 0;
    $("downloadViolations").onclick = () => downloadCSV("violations.csv", violations);
  }

  function downloadCSV(filename, rows) {
    if (!rows.length) return;
    const fields = [...new Set(rows.flatMap((row) => Object.keys(row)))];
    const cell = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;
    const csv = "\uFEFF" + [fields.join(","), ...rows.map((row) => fields.map((field) => cell(row[field])).join(","))].join("\r\n");
    const anchor = document.createElement("a");
    anchor.href = URL.createObjectURL(new Blob([csv], {type:"text/csv;charset=utf-8"}));
    anchor.download = filename; anchor.click(); URL.revokeObjectURL(anchor.href);
  }

  function parseCSV(text) {
    const rows = [];
    let row = [], cell = "", quoted = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (quoted) {
        if (c === '"' && text[i+1] === '"') { cell += '"'; i++; }
        else if (c === '"') quoted = false;
        else cell += c;
      } else if (c === '"') quoted = true;
      else if (c === ",") { row.push(cell); cell = ""; }
      else if (c === "\n") { row.push(cell.replace(/\r$/, "")); rows.push(row); row = []; cell = ""; }
      else cell += c;
    }
    if (cell.length || row.length) { row.push(cell.replace(/\r$/, "")); rows.push(row); }
    if (rows.length < 2) throw new Error("天气CSV没有数据行");
    const headers = rows.shift().map((x) => x.replace(/^\uFEFF/, "").trim());
    return rows.filter((r) => r.some((v) => v.trim())).map((r) => Object.fromEntries(headers.map((h,i) => [h,(r[i] || "").trim()])));
  }

  async function loadWeatherFile() {
    const file = $("weatherFile").files[0];
    if (!file) throw new Error("请先选择天气CSV");
    const rows = parseCSV(await file.text());
    const required = ["station_id","time_utc","cloud_percent"];
    if (required.some((key) => !(key in rows[0]))) throw new Error(`CSV必须包含列：${required.join(", ")}`);
    weather = rows.map((row) => {
      const station = Number(row.station_id), cloud = Number(row.cloud_percent), time = Date.parse(row.time_utc);
      if (!Number.isInteger(station) || station < 1 || station > 10 || !Number.isFinite(time) || !Number.isFinite(cloud) || cloud < 0 || cloud > 100) throw new Error(`天气数据无效：${JSON.stringify(row)}`);
      if (!/(Z|\+00:00)$/.test(row.time_utc)) throw new Error(`时间必须标成UTC（Z或+00:00）：${row.time_utc}`);
      const date = new Date(time);
      if (date.getUTCMinutes() || date.getUTCSeconds() || date.getUTCMilliseconds()) throw new Error(`天气时间必须为UTC整点：${row.time_utc}`);
      const epoch_s = (time - START) / 1000;
      if (epoch_s < 0 || epoch_s >= HORIZON) throw new Error(`天气记录不在本次6天规划范围内：${row.time_utc}`);
      return {station_id:station, epoch_s, time_utc:new Date(time).toISOString(), cloud_percent:cloud};
    }).sort((a,b) => a.epoch_s - b.epoch_s || a.station_id - b.station_id);
    const unique = new Set(weather.map((row) => `${row.station_id}|${row.epoch_s}`));
    if (unique.size !== weather.length) throw new Error("同一站点的天气时刻重复");
    $("weatherStatus").textContent = `${weather.length.toLocaleString()}条小时记录 · ${file.name}`;
    $("weatherStatus").className = "pill status-pass";
    renderWeather();
  }

  function weatherAt(stationId, timeSeconds) {
    const hour = Math.floor(timeSeconds / 3600) * 3600;
    return weather.find((row) => row.station_id === Number(stationId) && row.epoch_s === hour) || null;
  }

  function renderWeather() {
    if (!weather.length || !activePlan) {
      $("weatherHeatmap").innerHTML = `<p class="muted">尚未载入天气数据。请按上方CSV格式提供逐小时数据；本页不会虚构天气。</p>`;
      $("weatherTaskRows").innerHTML = "";
      return;
    }
    const hours = [...new Set(weather.map((row) => row.epoch_s))].sort((a,b) => a-b);
    const lookup = new Map(weather.map((row) => [`${row.station_id}|${row.epoch_s}`, row]));
    const head = `<div class="weather-row" style="--weather-cols:${hours.length}"><span class="weather-site">UTC</span>${hours.map((hour) => `<span class="weather-head" title="${esc(timeUTC(hour))}">${new Date(START+hour*1000).toISOString().slice(5,13)}</span>`).join("")}</div>`;
    const body = catalog.stations.map((site) => `<div class="weather-row" style="--weather-cols:${hours.length}"><span class="weather-site">站${site.station_id}</span>${hours.map((hour) => {
      const sample = lookup.get(`${site.station_id}|${hour}`);
      if (!sample) return `<span class="weather-cell missing" title="站点${site.station_id} ${timeUTC(hour)}：无数据"></span>`;
      const cls = sample.cloud_percent < 30 ? "low-cloud" : sample.cloud_percent < 70 ? "mid-cloud" : "high-cloud";
      return `<span class="weather-cell ${cls}" title="站点${site.station_id} ${timeUTC(hour)} · 云量${sample.cloud_percent.toFixed(1)}%"></span>`;
    }).join("")}</div>`).join("");
    $("weatherHeatmap").innerHTML = head + body;
    const taskRows = tasks().slice().sort((a,b) => a.start_s-b.start_s).slice(0,1000).map((task) => {
      const sample = weatherAt(task.station_id, task.start_s);
      return `<tr><td>${esc(timeUTC(task.start_s))}</td><td>${esc(task.target_id)}</td><td>${task.station_id}</td><td>${sample ? `${sample.cloud_percent.toFixed(1)}%` : "—"}</td><td>${sample ? "有小时样本（取任务开始所在UTC小时）" : "无匹配小时数据"}</td></tr>`;
    });
    $("weatherTaskRows").innerHTML = taskRows.join("") || `<tr><td colspan="5">所选排程没有任务。</td></tr>`;
  }

  function renderAll() {
    renderMap(); renderStationDetails(); renderTimeline(); renderComparison(); renderAcceptance(); renderWeather();
  }

  async function syncToStatusAnalysis() {
    if (!activePlan) return;
    const header = "target_id,station_id,start_s,end_s,duration_s";
    const lines = tasks().map((task) => [task.target_id,task.station_id,task.start_s,task.end_s,task.duration_s].join(","));
    const bytes = new TextEncoder().encode([header,...lines].join("\n"));
    let binary = ""; bytes.forEach((value) => { binary += String.fromCharCode(value); });
    const response = await jsonFetch("/api/analysis", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({schedule_base64:btoa(binary)})});
    if (typeof window.updateSatelliteAnalysis === "function") window.updateSatelliteAnalysis(response);
    document.querySelectorAll(".tab").forEach((button) => button.classList.toggle("active", button.dataset.view === "analysisView"));
    document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === "analysisView"));
    $("analysisStatus").textContent = `已使用${activePlan.label}生成状态分析；排程SHA-256 ${activePlan.sha256.slice(0,16)}…`;
  }

  async function init() {
    try {
      catalog = await jsonFetch("/api/dashboard/catalog");
      const select = $("sharedPlan");
      fillPlanSelect(select);
      initTimeControls();
      select.addEventListener("change", async () => {
        if (select.value.startsWith("uploaded:")) {
          const planId = select.value.slice("uploaded:".length);
          activePlan = uploadedPlans.get(planId) || activePlan;
          currentViolations = activePlan?.violations || [];
          if (activePlan) {
            $("dashboardSourceStatus").textContent = `${activePlan.label} · ${activePlan.metrics.violation_count}项违规 · ${activePlan.sha256.slice(0, 12)}…`;
            $("dashboardSourceStatus").className = `pill ${activePlan.metrics.legal ? "status-pass" : "status-fail"}`;
            renderAll();
          }
          return;
        }
        $("dashboardSourceStatus").textContent = "载入方案…";
        try { await loadPlan(select.value); } catch (error) { $("dashboardSourceStatus").textContent = error.message; }
      });
      $("loadDashboardUpload").addEventListener("click", async () => {
        try { await importPlan($("dashboardUpload").files[0]); }
        catch (error) { $("dashboardSourceStatus").textContent = error.message; $("dashboardSourceStatus").className = "pill status-fail"; }
      });
      window.addEventListener("schedule-ready", async (event) => {
        const jobId = event.detail?.job_id;
        if (!jobId) return;
        try {
          await loadPlan(jobId);
          let option = [...select.options].find((item) => item.value === jobId);
          if (!option) { option = document.createElement("option"); option.value = jobId; option.textContent = `本次生成方案 ${jobId}`; select.append(option); }
          select.value = jobId;
        } catch (error) { $("dashboardSourceStatus").textContent = `无法载入新排程：${error.message}`; }
      });
      $("timelineStart").addEventListener("change", renderTimeline);
      $("timelineHours").addEventListener("change", renderTimeline);
      $("timelineStation").addEventListener("change", renderTimeline);
      $("acceptanceSearch").addEventListener("input", () => { acceptancePage = 0; renderAcceptance(); });
      $("acceptancePageSize").addEventListener("change", () => { acceptancePage = 0; renderAcceptance(); });
      $("acceptancePrev").addEventListener("click", () => { acceptancePage = Math.max(0, acceptancePage - 1); renderAcceptance(); });
      $("acceptanceNext").addEventListener("click", () => { acceptancePage += 1; renderAcceptance(); });
      $("weatherFile").addEventListener("change", () => { $("weatherStatus").textContent = $("weatherFile").files[0]?.name || "尚未提供天气文件"; });
      $("loadWeather").addEventListener("click", async () => { try { await loadWeatherFile(); } catch (error) { $("weatherStatus").textContent = error.message; $("weatherStatus").className = "pill status-fail"; } });
      $("syncCurrentPlan").addEventListener("click", async () => { try { $("dashboardSourceStatus").textContent = "同步到卫星状态分析…"; await syncToStatusAnalysis(); } catch (error) { $("dashboardSourceStatus").textContent = error.message; } });
      select.value = catalog.plans.some((plan) => plan.id === "coverage_score_hybrid") ? "coverage_score_hybrid" : catalog.plans[0]?.id;
      if (select.value) await loadPlan(select.value);
      else throw new Error("没有可用的冻结基线排程");
    } catch (error) {
      $("dashboardSourceStatus").textContent = `展示数据加载失败：${error.message}`;
      $("dashboardSourceStatus").className = "pill status-fail";
    }
  }

  init();
})();
