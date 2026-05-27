import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000/api';

const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Token ${token}`;
  return config;
});

export const login = (username, password) =>
  api.post('/auth/login/', { username, password });
export const getStats = () => api.get('/stats/');
export const getRecords = (filters = {}) => api.get('/records/', { params: filters });
export const reviewRecord = (id, status, note = '') =>
  api.patch(`/records/${id}/review/`, { status, note });
export const ingestFile = (sourceType, file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post(`/ingest/${sourceType}/`, formData);
};

export default api;