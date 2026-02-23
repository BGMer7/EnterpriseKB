/**
 * 认证工具函数
 */
import { api } from "./api";

export interface User {
  id: string;
  wechat_id: string;
  name: string;
  email?: string;
  department_id?: string;
  avatar_url?: string;
  is_active: boolean;
  roles: string[];
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem("access_token");
}

export function getToken(): string | null {
  return localStorage.getItem("access_token");
}

export function getCurrentUser(): User | null {
  const userStr = localStorage.getItem("user");
  return userStr ? JSON.parse(userStr) : null;
}

export function hasRole(role: string): boolean {
  const user = getCurrentUser();
  return user?.roles.includes(role) ?? false;
}

export function hasAnyRole(roles: string[]): boolean {
  const user = getCurrentUser();
  return user ? roles.some((r) => user.roles.includes(r)) : false;
}

export function isAdmin(): boolean {
  return hasRole("SUPER_ADMIN");
}

export async function logout(): Promise<void> {
  try {
    await api.auth.logout();
  } catch (error) {
    console.error("Logout error:", error);
  } finally {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    window.location.href = "/auth/login";
  }
}
