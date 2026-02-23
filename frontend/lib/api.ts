/**
 * API客户端
 */
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token过期，尝试刷新
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });
          localStorage.setItem("access_token", response.data.access_token);
          error.config.headers.Authorization = `Bearer ${response.data.access_token}`;
          return apiClient.request(error.config);
        } catch (refreshError) {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/auth/login";
        }
      } else {
        window.location.href = "/auth/login";
      }
    }
    return Promise.reject(error);
  }
);

export const api = {
  // 认证
  auth: {
    login: (code: string) =>
      apiClient.post("/api/v1/auth/login", { code }),
    logout: () => apiClient.post("/api/v1/auth/logout"),
    getCurrentUser: () => apiClient.get("/api/v1/auth/me"),
  },

  // 对话
  chat: {
    query: (query: string, conversationId?: string) =>
      apiClient.post("/api/v1/chat/query", { query, conversation_id: conversationId }),
    submitFeedback: (messageId: string, feedback: string, comment?: string) =>
      apiClient.post("/api/v1/chat/feedback", {
        message_id: messageId,
        feedback,
        comment,
      }),
    getConversations: (page = 1, pageSize = 20) =>
      apiClient.get("/api/v1/chat/conversations", {
        params: { page, page_size: pageSize },
      }),
    getConversationMessages: (conversationId: string) =>
      apiClient.get(`/api/v1/chat/conversations/${conversationId}/messages`),
    deleteConversation: (conversationId: string) =>
      apiClient.delete(`/api/v1/chat/conversations/${conversationId}`),
    getSuggestedQuestions: () =>
      apiClient.get("/api/v1/chat/suggestions"),
  },

  // 文档
  documents: {
    upload: (file: File, data: any) => {
      const formData = new FormData();
      formData.append("file", file);
      Object.entries(data).forEach(([key, value]) => {
        formData.append(key, value);
      });
      return apiClient.post("/api/v1/documents/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    },
    list: (params?: any) => apiClient.get("/api/v1/documents", { params }),
    get: (id: string) => apiClient.get(`/api/v1/documents/${id}`),
    update: (id: string, data: any) => apiClient.put(`/api/v1/documents/${id}`, data),
    delete: (id: string) => apiClient.delete(`/api/v1/documents/${id}`),
    getChunks: (id: string) => apiClient.get(`/api/v1/documents/${id}/chunks`),
    publish: (id: string) => apiClient.post(`/api/v1/documents/${id}/publish`),
    reject: (id: string, comment?: string) =>
      apiClient.post(`/api/v1/documents/${id}/reject`, { comment }),
  },

  // 用户
  users: {
    list: (params?: any) => apiClient.get("/api/v1/users", { params }),
    get: (id: string) => apiClient.get(`/api/v1/users/${id}`),
    create: (data: any) => apiClient.post("/api/v1/users", data),
    update: (id: string, data: any) => apiClient.put(`/api/v1/users/${id}`, data),
    delete: (id: string) => apiClient.delete(`/api/v1/users/${id}`),
    assignRoles: (id: string, roleIds: string[]) =>
      apiClient.post(`/api/v1/users/${id}/roles`, { user_id: id, role_ids: roleIds }),
    getDepartments: () => apiClient.get("/api/v1/users/departments/list"),
    getRoles: () => apiClient.get("/api/v1/users/roles/list"),
  },

  // 管理后台
  admin: {
    getStats: (startDate?: string, endDate?: string) =>
      apiClient.get("/api/v1/admin/dashboard/stats", {
        params: { start_date: startDate, end_date: endDate },
      }),
    getAuditLogs: (filter?: any) => apiClient.get("/api/v1/admin/audit-logs", { params: filter }),
    getSystemConfig: () => apiClient.get("/api/v1/admin/system/config"),
    updateSystemConfig: (key: string, value: any) =>
      apiClient.put(`/api/v1/admin/system/config/${key}`, { value }),
    healthCheck: () => apiClient.get("/api/v1/admin/health"),
  },
};

export default api;
