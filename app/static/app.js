'use strict';
const $ = (id) => document.getElementById(id);
const statusText = { queued: 'Pendiente', running: 'Procesando', ready: 'Listo para revisar', failed: 'No completado' };
const state = { config: null, file: null, jobs: [], selected: null, renderKey: null, historyKey: null, offset: 0, total: 0, uploading: false };
const number = (n) => new Intl.NumberFormat('es-ES').format(n);
const seconds = (n) => `${Number(n).toLocaleString('es-ES', { maximumFractionDigits: 2 })} s`;
function notify(message) { $('notification').textContent = message; $('notification').hidden = !message; }
async function api(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'No se pudo completar la solicitud. Comprueba el archivo y las opciones.');
  return data;
}
function updateButton() {
  const busy = state.jobs.some((j) => ['queued', 'running'].includes(j.status));
  $('analyze-button').disabled = state.uploading || busy || !state.file || !state.config?.model_available;
  $('analyze-button').textContent = state.uploading ? 'Subiendo vídeo…' : busy ? 'Análisis en curso…' : 'Analizar vídeo ↗';
  $('upload-hint').textContent = busy ? 'Un análisis a la vez. El estado se actualiza automáticamente.' : state.file ? 'Listo para analizar en este equipo.' : 'Selecciona un archivo para comenzar.';
}
function chooseFile(file) {
  if (!file) return;
  if (state.config && file.size > state.config.max_upload_bytes) { notify('El archivo supera el tamaño permitido. Selecciona uno más pequeño.'); return; }
  state.file = file;
  $('file-label').textContent = file.name;
  $('file-info').textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB · archivo seleccionado`;
  notify(''); updateButton();
}
function badge(status) {
  const item = document.createElement('span'); item.className = `status ${status}`; item.textContent = statusText[status] || status; return item;
}
function renderHistory() {
  const key = JSON.stringify([state.selected, state.jobs.map((job) => [job.id, job.status, job.updated_at])]);
  if (key === state.historyKey) return;
  state.historyKey = key;
  const list = $('history-list'); list.replaceChildren();
  if (!state.jobs.length) {
    const empty = document.createElement('p'); empty.className = 'empty'; empty.textContent = 'Tu primer análisis aparecerá aquí.\nEmpieza subiendo un vídeo.'; list.append(empty); return;
  }
  for (const job of state.jobs) {
    const row = document.createElement('button'); row.type = 'button'; row.className = `history-item ${job.id === state.selected ? 'selected' : ''}`;
    row.setAttribute('aria-label', `Abrir análisis: ${job.filename} · ${statusText[job.status]}`);
    const icon = document.createElement('span'); icon.className = 'file-icon'; icon.textContent = '▷'; icon.setAttribute('aria-hidden', 'true');
    const details = document.createElement('span'); details.className = 'file-details';
    const title = document.createElement('strong'); title.textContent = job.filename;
    const date = document.createElement('small'); date.textContent = new Date(job.created_at).toLocaleString('es-ES', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
    details.append(title, date); row.append(icon, details, badge(job.status));
    row.addEventListener('click', () => selectJob(job.id)); list.append(row);
  }
}
function artifact(id, name, download = false) { return `/api/analyses/${encodeURIComponent(id)}/files/${name}${download ? '?download=true' : ''}`; }
async function selectJob(id) {
  state.selected = id; state.renderKey = null; state.offset = 0;
  renderHistory();
  try { renderJob(await api(`/api/analyses/${id}`)); } catch (error) { notify(error.message); }
}
function renderJob(job) {
  const key = `${job.id}/${job.status}/${job.updated_at}`;
  if (key === state.renderKey) return;
  state.renderKey = key;
  $('result').hidden = false;
  $('result-name').textContent = job.filename;
  $('result-status').className = `status ${job.status}`;
  $('result-status').textContent = statusText[job.status];
  $('result-content').hidden = job.status !== 'ready';
  $('job-message').hidden = job.status === 'ready';
  $('job-message').className = `job-message ${job.status}`;
  $('job-message').textContent = job.status === 'failed' ? job.error || 'No se pudo completar el análisis.' : job.status === 'queued' ? 'El vídeo está listo para procesarse.' : 'Analizando todos los fotogramas. Puedes consultar esta página mientras trabaja; al cerrar la aplicación se interrumpe el proceso.';
  if (job.status === 'ready') {
    const report = job.report;
    $('duration').textContent = seconds(report.source.duration_seconds);
    $('frames').textContent = number(report.frames_processed);
    $('count').textContent = number(report.detection_count);
    $('elapsed').textContent = seconds(report.elapsed_seconds);
    $('result-video').src = artifact(job.id, 'video');
    $('result-video').poster = artifact(job.id, 'preview');
    for (const [id, name] of [['download-video', 'video'], ['download-csv', 'csv'], ['download-report', 'report']]) $(''+id).href = artifact(job.id, name, true);
    loadDetections().catch((error) => notify(error.message));
  } else {
    $('result-video').pause(); $('result-video').removeAttribute('src'); $('result-video').load();
  }
}
async function loadDetections() {
  const id = state.selected, offset = state.offset;
  if (!id) return;
  const data = await api(`/api/analyses/${id}/detections?offset=${offset}&limit=50`);
  if (id !== state.selected || offset !== state.offset) return;
  state.total = data.total;
  const body = $('detections-body'); body.replaceChildren();
  if (!data.items.length) {
    const row = document.createElement('tr'), cell = document.createElement('td'); cell.colSpan = 3;
    cell.textContent = 'Sin propuestas con este umbral. Esto no demuestra ausencia de logos.'; row.append(cell); body.append(row);
  }
  for (const detection of data.items) {
    const row = document.createElement('tr'), instant = document.createElement('td'), confidence = document.createElement('td'), review = document.createElement('td');
    const seek = document.createElement('button'); seek.className = 'seek-button'; seek.textContent = seconds(detection.timestamp_seconds);
    seek.title = `Ver fotograma ${detection.frame_index}`;
    seek.addEventListener('click', () => {
      const video = $('result-video');
      const play = () => { video.currentTime = detection.timestamp_seconds; video.play().catch(() => {}); };
      if (video.readyState >= 1) play(); else video.addEventListener('loadedmetadata', play, { once: true });
    });
    instant.append(seek); confidence.textContent = `${(detection.confidence * 100).toFixed(1)} %`;
    const tag = document.createElement('span'); tag.className = 'review-tag'; tag.textContent = 'Sin revisar'; review.append(tag);
    row.append(instant, confidence, review); body.append(row);
  }
  $('page-label').textContent = data.total ? `${offset + 1}–${Math.min(offset + 50, data.total)} de ${number(data.total)}` : '0 propuestas';
  $('previous').disabled = offset === 0; $('next').disabled = offset + 50 >= data.total;
}
async function refresh() {
  const data = await api('/api/analyses'); state.jobs = data.items; renderHistory(); updateButton();
  if (!state.selected && state.jobs.length) state.selected = state.jobs[0].id;
  const selected = state.jobs.find((job) => job.id === state.selected);
  if (selected) renderJob(selected);
}
$('video-file').addEventListener('change', (event) => chooseFile(event.target.files[0]));
for (const type of ['dragenter', 'dragover']) $('dropzone').addEventListener(type, (event) => { event.preventDefault(); $('dropzone').classList.add('dragover'); });
for (const type of ['dragleave', 'drop']) $('dropzone').addEventListener(type, (event) => { event.preventDefault(); $('dropzone').classList.remove('dragover'); });
$('dropzone').addEventListener('drop', (event) => chooseFile(event.dataTransfer.files[0]));
$('confidence').addEventListener('input', () => { $('confidence-value').textContent = Number($('confidence').value).toLocaleString('es-ES', { minimumFractionDigits: 2 }); });
$('refresh').addEventListener('click', () => refresh().catch((error) => notify(error.message)));
$('previous').addEventListener('click', () => { state.offset = Math.max(0, state.offset - 50); loadDetections().catch((error) => notify(error.message)); });
$('next').addEventListener('click', () => { state.offset += 50; loadDetections().catch((error) => notify(error.message)); });
$('upload-form').addEventListener('submit', async (event) => {
  event.preventDefault(); if (!state.file || $('analyze-button').disabled) return;
  state.uploading = true; updateButton(); notify('');
  const form = new FormData(); form.append('video', state.file, state.file.name); form.append('confidence', $('confidence').value);
  try {
    const job = await api('/api/analyses', { method: 'POST', body: form });
    state.selected = job.id; state.renderKey = null; state.offset = 0;
    renderJob(job); await refresh();
  } catch (error) { notify(error.message); }
  finally { state.uploading = false; updateButton(); }
});
async function poll() {
  try { await refresh(); } catch (error) { notify('No se pudo conectar con la aplicación local. Comprueba que siga abierta.'); }
  setTimeout(poll, 2000);
}
(async () => {
  try {
    state.config = await api('/api/config');
    $('limits').textContent = `Hasta ${Math.round(state.config.max_upload_bytes / 1024 / 1024)} MB · ${state.config.max_duration_seconds} s · ${(state.config.max_pixels / 1000000).toFixed(1)} MP`;
    $('model-state').textContent = state.config.model_available ? 'NOX texto · modelo experimental' : 'Modelo no disponible';
    updateButton(); await poll();
  } catch (error) { notify(error.message); }
})();
