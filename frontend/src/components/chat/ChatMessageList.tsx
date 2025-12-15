"use client";
import { useState } from "react";
import { ChatMessage } from "@/hooks/use-chat";
import { cn } from "@/lib/utils";
import { ThumbsUp, ThumbsDown } from "lucide-react";
import { apiSubmitFeedback } from "@/lib/api";

interface ChatMessageListProps {
  messages: ChatMessage[];
}

const ACCESS_TOKEN_KEY = "access_token";

export function ChatMessageList({ messages }: ChatMessageListProps) {
  const [feedbackGiven, setFeedbackGiven] = useState<Set<string>>(new Set());

  const handleFeedback = async (
    messageId: string,
    rating: 1 | 5,
    answer: string,
    question: string,
  ) => {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (!token) return;

    try {
      await apiSubmitFeedback(token, {
        question,
        answer,
        rating,
      });

      // Update local state to show feedback was given
      setFeedbackGiven((prev) => {
        const newSet = new Set(prev);
        newSet.add(messageId);
        return newSet;
      });
    } catch (error) {
      console.error("Error submitting feedback:", error);
      // Optionally show a toast error
    }
  };

  if (messages.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 px-4 text-center">
        <p className="text-sm font-medium text-foreground">
          Nenhuma conversa ainda.
        </p>
        <p className="text-xs text-muted-foreground max-w-sm">
          Envie uma pergunta sobre os documentos da sua empresa e o Company
          Buddy vai responder usando apenas o que foi indexado.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-6 overflow-y-auto px-4 py-3">
      {messages.map((message, index) => {
        // Try to find the preceding user message for context
        const questionText =
          index > 0 && messages[index - 1].role === "user"
            ? messages[index - 1].content
            : "Pergunta desconhecida";

        const isAssistant = message.role === "assistant";
        const hasFeedback = feedbackGiven.has(message.id);

        return (
          <div
            key={message.id}
            className={cn(
              "flex w-full flex-col gap-2",
              !isAssistant ? "items-end" : "items-start",
            )}
          >
            <div
              className={cn(
                "max-w-[85%] rounded-2xl px-5 py-3 text-sm shadow-sm leading-relaxed",
                !isAssistant
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-800 text-slate-200 border border-slate-700",
              )}
            >
              {message.content}
            </div>

            {/* Sources & Metadata (Only for Assistant) */}
            {isAssistant && (
              <div className="ml-2 flex flex-col gap-2 max-w-[85%]">
                {/* Sources Section */}
                {message.sources && message.sources.length > 0 && (
                  <div className="rounded-lg bg-slate-900/50 p-3 text-xs text-slate-400 border border-slate-800/50">
                    <div className="mb-2 font-semibold text-indigo-400 flex items-center gap-2">
                      <span>📚 Fontes Utilizadas</span>
                    </div>
                    <ul className="space-y-2">
                      {message.sources.map((source, idx) => (
                        <li
                          key={`${idx}-${source.documentName}`}
                          className="flex flex-col gap-1"
                        >
                          <div className="flex items-baseline justify-between">
                            <span className="font-medium text-slate-300">
                              {source.documentName}
                            </span>
                            {typeof source.score === "number" && (
                              <span
                                className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                                  source.score > 0.7
                                    ? "bg-emerald-500/10 text-emerald-400"
                                    : "bg-slate-700 text-slate-400"
                                }`}
                              >
                                {(source.score * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                          {source.chunkPreview && (
                            <div className="pl-2 border-l-2 border-slate-700 text-[11px] italic text-slate-500 line-clamp-2">
                              "{source.chunkPreview}"
                            </div>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Feedback Actions */}
                <div className="flex items-center gap-2 mt-1">
                  <button
                    onClick={() =>
                      handleFeedback(
                        message.id,
                        5,
                        message.content,
                        questionText,
                      )
                    }
                    disabled={hasFeedback}
                    className={cn(
                      "flex items-center gap-1.5 px-2 py-1 rounded hover:bg-slate-800 transition-colors text-xs font-medium",
                      hasFeedback
                        ? "opacity-50 cursor-not-allowed"
                        : "text-slate-400 hover:text-emerald-400",
                    )}
                    title="Útil"
                  >
                    <ThumbsUp className="w-3.5 h-3.5" />
                    <span>Útil</span>
                  </button>
                  <button
                    onClick={() =>
                      handleFeedback(
                        message.id,
                        1,
                        message.content,
                        questionText,
                      )
                    }
                    disabled={hasFeedback}
                    className={cn(
                      "flex items-center gap-1.5 px-2 py-1 rounded hover:bg-slate-800 transition-colors text-xs font-medium",
                      hasFeedback
                        ? "opacity-50 cursor-not-allowed"
                        : "text-slate-400 hover:text-red-400",
                    )}
                    title="Não foi útil"
                  >
                    <ThumbsDown className="w-3.5 h-3.5" />
                    <span>Não útil</span>
                  </button>
                  {hasFeedback && (
                    <span className="text-[10px] text-slate-500 animate-in fade-in ml-2">
                      Obrigado pelo feedback!
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
