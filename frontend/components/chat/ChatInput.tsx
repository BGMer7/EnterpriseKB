/**
 * 聊天输入组件
 */
"use client";

import { useState } from "react";
import { Send, Mic } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  disabled = false,
  placeholder = "请输入您的问题...",
}: ChatInputProps) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (input.trim()) {
      onSend(input.trim());
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-end gap-2 bg-card border rounded-lg p-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none bg-transparent border-0 outline-none p-2 min-h-[40px]"
          style={{
            height: "auto",
            maxHeight: "200px",
          }}
          onInput={(e) => {
            const target = e.target as HTMLTextAreaElement;
            target.style.height = "auto";
            target.style.height = target.scrollHeight + "px";
          }}
        />
        <Button
          size="icon"
          onClick={handleSend}
          disabled={disabled || !input.trim()}
        >
          <Send className="w-4 h-4" />
        </Button>
        <Button
          size="icon"
          variant="secondary"
          disabled={disabled}
        >
          <Mic className="w-4 h-4" />
        </Button>
      </div>
      <p className="text-xs text-muted-foreground mt-2 text-center">
        按 Enter 发送，Shift + Enter 换行
      </p>
    </div>
  );
}
