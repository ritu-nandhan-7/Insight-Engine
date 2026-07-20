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

// Intercept errors to extract the backend's detail message
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data) {
      const data = error.response.data;
      // Backend returns: {"detail": {"status": "error", "detail": "message"}}
      // or FastAPI default: {"detail": "message"}
      const message =
        typeof data.detail === "object" && data.detail?.detail
          ? data.detail.detail
          : typeof data.detail === "string"
            ? data.detail
            : null;
      if (message) {
        error.message = message;
      }
    }
    return Promise.reject(error);
  },
);
