const API = 'http://127.0.0.1:8000/api';
async function request(path: string, options: RequestInit = {}) {
  const response = await fetch(`${API}${path}`, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try { const body = await response.json(); message = body.detail || message; } catch {}
    throw new Error(message);
  }
  return response;
}
export async function getJSON(path: string) { return (await request(path)).json(); }
export async function postJSON(path: string, body?: unknown) {
  return (await request(path, { method: 'POST', headers: {'Content-Type':'application/json'}, body: body ? JSON.stringify(body) : undefined })).json();
}
export async function uploadCSV(file: File) {
  const form = new FormData(); form.append('file', file);
  return (await request('/students/import-csv', {method:'POST', body:form})).json();
}
export function download(path: string) { window.open(`${API}${path}`, '_blank'); }
