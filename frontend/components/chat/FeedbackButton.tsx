/**
 * 反馈按钮组件
 */
"use client";

import { useState } from "react";
import { ThumbsUp, ThumbsDown } from "lucide-react";
import { Button } from "@/components/ui/button";

interface FeedbackButtonProps {
  messageId: string;
  onFeedback?: (feedback: "helpful" | "not_helpful" | "inaccurate") => void;
}

export function FeedbackButton({ messageId, onFeedback }: FeedbackButtonProps) {
  const [feedback, setFeedback] = useState<"helpful" | "not_helpful" | "inaccurate" | null>(null);

  const handleFeedback = (type: "helpful" | "not_helpful" | "inaccurate") => {
    setFeedback(type);
    onFeedback?.(type);

    // TODO: 发送反馈到API
    fetch("/api/v1/chat/feedback", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      },
      body: JSON.stringify({
        message_id: messageId,
        feedback: type,
      }),
    });
  };

  return (
    <div className="flex items-center gap-1 mt-2">
      <Button
        size="sm"
        variant={feedback === "helpful" ? "default" : "ghost"}
        onClick={() => handleFeedback("helpful")}
        className="h-8"
      >
        <ThumbsUp className="w-4 h-4" />
      </Button>
      <Button
        size="sm"
        variant={feedback === "not_helpful" ? "default" : "ghost"}
        onClick={() => handleFeedback("not_helpful")}
        className="h-8"
      >
        <ThumbsDown className="w-4 h-4" />
      </Button>
    </div>
  );
}
