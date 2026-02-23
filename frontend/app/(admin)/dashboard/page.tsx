/**
 * 数据看板页面
 */
"use client";

import { useEffect, useState } from "react";

interface DashboardStats {
  totalUsers: number;
  totalDocuments: number;
  totalConversations: number;
  totalQueries: number;
  todayQueries: number;
  avgResponseTime: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // TODO: 从API获取统计数据
    setStats({
      totalUsers: 156,
      totalDocuments: 89,
      totalConversations: 1245,
      totalQueries: 3892,
      todayQueries: 234,
      avgResponseTime: 3.2,
    });
    setLoading(false);
  }, []);

  if (loading) {
    return <div className="p-8">加载中...</div>;
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold mb-6">数据看板</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <StatCard
          title="总用户数"
          value={stats?.totalUsers || 0}
          change="+12%"
        />
        <StatCard
          title="总文档数"
          value={stats?.totalDocuments || 0}
          change="+5%"
        />
        <StatCard
          title="今日查询"
          value={stats?.todayQueries || 0}
          change="+18%"
        />
        <StatCard
          title="总查询数"
          value={stats?.totalQueries || 0}
          change="+23%"
        />
        <StatCard
          title="对话数"
          value={stats?.totalConversations || 0}
          change="+15%"
        />
        <StatCard
          title="平均响应时间"
          value={`${stats?.avgResponseTime || 0}s`}
          change="-8%"
        />
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  change,
}: {
  title: string;
  value: number | string;
  change: string;
}) {
  const isPositive = change.startsWith("+");

  return (
    <div className="bg-card border rounded-lg p-6">
      <div className="text-sm text-muted-foreground mb-2">{title}</div>
      <div className="text-2xl font-semibold mb-2">{value}</div>
      <div
        className={`text-sm ${
          isPositive ? "text-green-600" : "text-red-600"
        }`}
      >
        {change}
      </div>
    </div>
  );
}
