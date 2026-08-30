import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: {
    'Authorization': `Bearer ${import.meta.env.VITE_ADMIN_API_KEY || '<YOUR_ADMIN_API_KEY>'}`
  }
});

export const getMetrics = () => api.get('/metrics').then(res => res.data);
export const getRequests = () => api.get('/requests').then(res => res.data);
export const getModels = () => api.get('/models').then(res => res.data);
export const getCacheStats = () => api.get('/cache/stats').then(res => res.data);
