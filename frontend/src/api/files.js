async function request(path, options = {}) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.error?.message || `Request failed (${response.status}). Please try again.`);
  return body;
}
export const listFiles = (page = 1, signal) => request(`/api/files/?page=${page}&page_size=10`, {signal});
export const getFile = (id, signal) => request(`/api/files/${id}/`, {signal});
export const getMeasurements = (id, page, type, signal) => request(`/api/files/${id}/measurements/?page=${page}&page_size=25${type ? `&geometry_type=${encodeURIComponent(type)}` : ''}`, {signal});
export const uploadFile = file => { const body = new FormData(); body.append('file', file); return request('/api/files/', {method: 'POST', body}); };
