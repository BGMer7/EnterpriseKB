/**
 * 主对话页面
 */
"use client";

import { useState } from "react";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { ChatInput } from "@/components/chat/ChatInput";
import { SuggestionChips } from "@/components/chat/SuggestionChips";
import { SUGGESTED_QUESTIONS } from "@/lib/constants";

export default function ChatPage() {
  const [messages, setMessages] = useState<Array<{
    id: string;
    role: "user" | "assistant";
    content: string;
    sources?: Array<{
      documentId: string;
      documentTitle: string;
      section?: string;
      content: string;
    }>;
  }>>([]);

  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (content: string) => {
    // 添加用户消息
    const userMessage = {
      id: Date.now().toString(),
      role: "user" as const,
      content,
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // 调用后端API获取回复
      const response = await fetch("/api/chat/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: content }),
      });

      if (!response.ok) {
        throw new Error("Failed to get response");
      }

      const data = await response.json();

      // 添加助手回复
      const assistantMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant" as const,
        content: data.answer,
        sources: data.sources,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Error sending message:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="max-w-2xl mx-auto pt-8">
            <h2 className="text-2xl font-semibold mb-4">
              您好，我是企业制度查询助手
            </h2>
            <p className="text-muted-foreground mb-8">
              我可以帮您查询公司各类制度，如考勤、报销、请假、福利等。
            </p>
            <SuggestionChips
              questions={SUGGESTED_QUESTIONS}
              onSelect={handleSendMessage}
            />
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isLoading && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary" />
                正在思考...
              </div>
            )}
          </div>
        )}
      </div>

      {/* 输入框 */}
      <div className="border-t p-4">
        <ChatInput
          onSend={handleSendMessage}
          disabled={isLoading}
          placeholder="请输入您的问题..."
        />
      </div>
    </div>
  );
}
