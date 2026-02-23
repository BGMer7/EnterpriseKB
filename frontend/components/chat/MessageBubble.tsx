/**
 * 消息气泡组件
 */
import { User, Bot } from "lucide-react";
import { CitationCard } from "./CitationCard";

interface MessageBubbleProps {
  message: {
    id: string;
    role: "user" | "assistant";
    content: string;
    sources?: Array<{
      documentId: string;
      documentTitle: string;
      section?: string;
      content: string;
    }>;
  };
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? "bg-primary text-primary-foreground" : "bg-secondary"
        }`}
      >
        {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
      </div>
      <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} max-w-[80%]`}>
        <div
          className={`rounded-lg px-4 py-3 ${
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-secondary"
          }`}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        {message.sources && message.sources.length > 0 && !isUser && (
          <div className="mt-2">
            <p className="text-xs text-muted-foreground mb-2">参考来源：</p>
            {message.sources.map((source, index) => (
              <CitationCard key={index} source={source} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
