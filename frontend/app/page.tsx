/**
 * 首页
 * 根据用户状态重定向到登录页或对话页面
 */
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    // 检查登录状态
    const token = localStorage.getItem("access_token");
    if (token) {
      router.push("/chat");
    } else {
      router.push("/auth/login");
    }
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
        <p className="text-muted-foreground">正在跳转...</p>
      </div>
    </div>
  );
}
