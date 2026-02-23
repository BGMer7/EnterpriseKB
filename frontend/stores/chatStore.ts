/**
 * 对话状态管理
 */
import { create } from "zustand";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: Array<{
    documentId: string;
    documentTitle: string;
    section?: string;
    content: string;
  }>;
  timestamp: Date;
}

interface Conversation {
  id: string;
  title?: string;
  createdAt: Date;
  updatedAt: Date;
}

interface ChatState {
  currentConversation: Conversation | null;
  conversations: Conversation[];
  messages: Message[];
  isLoading: boolean;
  setCurrentConversation: (conv: Conversation | null) => void;
  addMessage: (message: Omit<Message, "timestamp">) => void;
  setLoading: (loading: boolean) => void;
  loadConversations: () => Promise<void>;
  loadMessages: (conversationId: string) => Promise<void>;
  createNewConversation: () => Promise<Conversation>;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  currentConversation: null,
  conversations: [],
  messages: [],
  isLoading: false,

  setCurrentConversation: (conv) => set({ currentConversation: conv }),

  addMessage: (message) =>
    set((state) => ({
      messages: [
        ...state.messages,
        { ...message, timestamp: new Date() },
      ],
    })),

  setLoading: (loading) => set({ isLoading: loading }),

  clearMessages: () => set({ messages: [] }),

  loadConversations: async () => {
    try {
      const response = await fetch("/api/v1/chat/conversations", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
      const data = await response.json();
      set({ conversations: data.conversations });
    } catch (error) {
      console.error("Failed to load conversations:", error);
    }
  },

  loadMessages: async (conversationId: string) => {
    try {
      set({ isLoading: true });
      const response = await fetch(
        `/api/v1/chat/conversations/${conversationId}/messages`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        }
      );
      const data = await response.json();
      set({ messages: data });
    } catch (error) {
      console.error("Failed to load messages:", error);
    } finally {
      set({ isLoading: false });
    }
  },

  createNewConversation: async () => {
    try {
      const response = await fetch("/api/v1/chat/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify({ query: "你好" }),
      });
      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Failed to create conversation:", error);
      throw error;
    }
  },
}));
