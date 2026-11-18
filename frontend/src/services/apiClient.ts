import axios, { AxiosInstance } from 'axios';

const STORAGE_KEY = 'pathsnap_api_base_url';
export const DEFAULT_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function getStoredBaseUrl(): string {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && saved.trim()) {
      return saved.trim();
    }
  } catch (e) {
    console.warn('Unable to access localStorage for API base URL', e);
  }
  return DEFAULT_BASE_URL;
}

export function setStoredBaseUrl(newUrl: string): void {
  try {
    const clean = newUrl.trim().replace(/\/+$/, ''); // Remove trailing slashes
    localStorage.setItem(STORAGE_KEY, clean);
    apiClient.defaults.baseURL = clean;
  } catch (e) {
    console.error('Failed to save API base URL to localStorage', e);
  }
}

export function resetStoredBaseUrl(): string {
  try {
    localStorage.removeItem(STORAGE_KEY);
    apiClient.defaults.baseURL = DEFAULT_BASE_URL;
  } catch (e) {
    console.error('Failed to reset API base URL', e);
  }
  return DEFAULT_BASE_URL;
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: getStoredBaseUrl(),
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

// Update baseURL on each request in case it was changed dynamically
apiClient.interceptors.request.use((config) => {
  config.baseURL = getStoredBaseUrl();
  return config;
});
