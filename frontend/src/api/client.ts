/** Configured Axios instance for backend API communication. */

import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// Generate a unique session ID once per browser tab
const _sessionId = crypto.randomUUID();

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
    "X-Session-ID": _sessionId,
  },
  withCredentials: true,
});
