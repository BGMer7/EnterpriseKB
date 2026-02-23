# EnterpriseKB Frontend

企业内部制度查询助手前端应用

## 技术栈

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui
- Zustand (状态管理)
- Axios (HTTP客户端)

## 快速开始

### 安装依赖

```bash
npm install
```

### 配置环境变量

创建 `.env.local` 文件：

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WECHAT_CORP_ID=your_corp_id
NEXT_PUBLIC_WECHAT_APP_ID=your_app_id
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

### 构建

```bash
npm run build
npm start
```

## 项目结构

```
frontend/
├── app/                       # Next.js App Router
│   ├── (chat)/                # 对话界面
│   ├── (admin)/               # 管理后台
│   ├── auth/                  # 认证页面
│   ├── api/                   # API Routes
│   ├── layout.tsx
│   └── page.tsx
├── components/                # 组件
│   ├── chat/                  # 对话相关组件
│   ├── admin/                 # 管理后台组件
│   └── ui/                    # shadcn/ui组件
├── lib/                       # 工具库
│   ├── api.ts
│   ├── auth.ts
│   ├── constants.ts
│   └── utils.ts
├── stores/                    # Zustand状态管理
├── hooks/                     # 自定义Hooks
├── types/                     # TypeScript类型
└── styles/                    # 样式文件
```

## 主要功能

### 对话界面
- 多轮对话
- 引用溯源
- 预设问题
- 反馈机制
- 流式响应

### 管理后台
- 数据看板
- 文档管理
- QA对管理
- 用户管理
- 系统设置
