"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { createElement } from "react";

interface ToastMessage {
  id: number;
  text: string;
  type: "success" | "error" | "info";
}

interface ToastCtx {
  toast: (text: string, type?: ToastMessage["type"]) => void;
}

const ToastContext = createContext<ToastCtx>({ toast: () => {} });

let nextId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ToastMessage[]>([]);

  const toast = useCallback((text: string, type: ToastMessage["type"] = "info") => {
    const id = nextId++;
    setMessages((prev) => [...prev, { id, text, type }]);
    setTimeout(() => {
      setMessages((prev) => prev.filter((m) => m.id !== id));
    }, 4000);
  }, []);

  const bgMap = {
    success: "bg-emerald-600",
    error: "bg-red-600",
    info: "bg-indigo-600",
  };

  return createElement(
    ToastContext.Provider,
    { value: { toast } },
    children,
    createElement(
      "div",
      { className: "fixed bottom-4 right-4 z-50 flex flex-col gap-2" },
      messages.map((m) =>
        createElement(
          "div",
          {
            key: m.id,
            className: `${bgMap[m.type]} text-white px-4 py-2 rounded-md shadow-lg text-sm animate-in fade-in slide-in-from-bottom-2`,
          },
          m.text
        )
      )
    )
  );
}

export function useToast() {
  return useContext(ToastContext);
}
