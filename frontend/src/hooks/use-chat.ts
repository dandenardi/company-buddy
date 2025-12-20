"use client";

import { useCallback, useState } from "react";
import { API_URL } from "@/lib/api";

export type ChatRole = "user" | "assistant" | "system";

export interface ChatSource {
  documentId: string;
  documentName: string;
  score?: number;
  chunkPreview?: string;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: Date;
  sources?: ChatSource[];
}

interface UseChatOptions {
  apiBaseUrl?: string;
}

interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  errorMessage: string | null;
  sendMessage: (question: string) => Promise<void>;
  clearMessages: () => void;
}

export function useChat(options?: UseChatOptions): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const apiBaseUrl = options?.apiBaseUrl || API_URL;

  const clearMessages = useCallback(() => {
    setMessages([]);
    setErrorMessage(null);
  }, []);

  const sendMessage = useCallback(
    async (question: string) => {
      if (!question.trim()) {
        return;
      }

      setErrorMessage(null);

      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: question,
        createdAt: new Date(),
      };

      // Otimista: já mostra a pergunta na tela
      setMessages((previousMessages) => [...previousMessages, userMessage]);
      setIsLoading(true);

      try {
        const accessToken =
          typeof window !== "undefined"
            ? window.localStorage.getItem("access_token")
            : null;

        if (!accessToken) {
          throw new Error(
            "Token de acesso não encontrado. Faça login novamente.",
          );
        }

        const response = await fetch(`${apiBaseUrl}/ask`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({
            question,
            // Se você tiver filtro por documento, pode passar algo como:
            // document_id: selectedDocumentId,
          }),
        });

        if (!response.ok) {
          const responseBody = await response.text();
          throw new Error(
            `Erro na API (/ask): ${response.status} - ${response.statusText} - ${responseBody}`,
          );
        }

        const data = await response.json();

        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: data.answer ?? "Não foi possível obter uma resposta.",
          createdAt: new Date(),
          sources: Array.isArray(data.sources)
            ? data.sources.map((source: any) => ({
                documentId: String(
                  source.document_id ?? source.documentId ?? "",
                ),
                documentName: String(
                  source.document_name ?? source.documentName ?? "Documento",
                ),
                score:
                  typeof source.score === "number" ? source.score : undefined,
                chunkPreview:
                  source.chunk_preview ?? source.chunkPreview ?? undefined,
              }))
            : [],
        };

        setMessages((previousMessages) => [
          ...previousMessages,
          assistantMessage,
        ]);
      } catch (error: unknown) {
        console.error("Erro ao enviar mensagem para /ask:", error);
        const message =
          error instanceof Error
            ? error.message
            : "Erro inesperado ao processar sua pergunta.";
        setErrorMessage(message);
      } finally {
        setIsLoading(false);
      }
    },
    [apiBaseUrl],
  );

  return {
    messages,
    isLoading,
    errorMessage,
    sendMessage,
    clearMessages,
  };
}
