/**
 * 企业微信OAuth回调页面
 */
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading"
  );
  const [message, setMessage] = useState("");

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get("code");

        if (!code) {
          setStatus("error");
          setMessage("授权失败：未获取到授权码");
          return;
        }

        // 调用后端登录接口
        const response = await fetch("/api/v1/auth/login", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ code }),
        });

        if (!response.ok) {
          throw new Error("登录失败");
        }

        const data = await response.json();

        // 保存token
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);

        // 保存用户信息
        localStorage.setItem("user", JSON.stringify(data.user));

        setStatus("success");
        setMessage("登录成功，正在跳转...");

        // 跳转到对话页面
        setTimeout(() => {
          router.push("/chat");
        }, 1000);
      } catch (error) {
        console.error("Auth error:", error);
        setStatus("error");
        setMessage("登录失败，请重试");
      }
    };

    handleCallback();
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        {status === "loading" && (
          <div className="space-y-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto" />
            <p className="text-muted-foreground">正在登录...</p>
          </div>
        )}

        {status === "success" && (
          <div className="space-y-4">
            <div className="text-green-600 text-4xl">✓</div>
            <p>{message}</p>
          </div>
        )}

        {status === "error" && (
          <div className="space-y-4">
            <div className="text-red-600 text-4xl">✕</div>
            <p className="text-destructive">{message}</p>
            <Button onClick={() => router.push("/auth/login")}>
              重新登录
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
