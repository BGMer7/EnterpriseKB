/**
 * 企业微信登录页面（演示模式）
 */
"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { MessageCircle, LogIn } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // 检查是否已有token
    if (localStorage.getItem("access_token")) {
      router.push("/chat");
      return;
    }

    // 检查是否配置了企业微信
    const WECHAT_CORP_ID = process.env.NEXT_PUBLIC_WECHAT_CORP_ID;
    const WECHAT_APP_ID = process.env.NEXT_PUBLIC_WECHAT_APP_ID;

    if (WECHAT_CORP_ID && WECHAT_APP_ID) {
      // 如果配置了企业微信，自动跳转
      const REDIRECT_URI = encodeURIComponent(
        `${window.location.origin}/auth/callback`
      );
      const url = `https://open.weixin.qq.com/connect/oauth2/authorize?appid=${WECHAT_APP_ID}&redirect_uri=${REDIRECT_URI}&response_type=code&scope=snsapi_base&state=STATE#wechat_redirect`;
      window.location.href = url;
    }
  }, [router]);

  const handleDemoLogin = () => {
    setLoading(true);
    // 使用模拟token
    localStorage.setItem("access_token", "demo_token_xxx");
    localStorage.setItem("user_id", "1");
    localStorage.setItem("user_name", "演示用户");
    setTimeout(() => {
      router.push("/chat");
    }, 500);
  };

  const WECHAT_CONFIGURED = !!(process.env.NEXT_PUBLIC_WECHAT_CORP_ID && process.env.NEXT_PUBLIC_WECHAT_APP_ID);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="text-center max-w-md mx-auto p-6">
        <div className="flex items-center justify-center mb-6">
          <MessageCircle className="w-16 h-16 text-blue-600" />
        </div>
        <h1 className="text-2xl font-semibold mb-2">
          EnterpriseKB
        </h1>
        <p className="text-muted-foreground mb-8">
          企业制度查询助手
        </p>

        {WECHAT_CONFIGURED ? (
          <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary" />
            正在跳转到企业微信...
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground mb-6">
              演示模式 - 使用模拟账户登录
            </p>
            <button
              onClick={handleDemoLogin}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-3 px-6 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <LogIn className="w-5 h-5" />
              {loading ? "登录中..." : "演示登录"}
            </button>
            <p className="text-xs text-muted-foreground">
              （无需企业微信配置，直接体验功能）
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
