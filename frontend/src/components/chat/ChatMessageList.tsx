"use client";
import { ChatMessage } from "@/hooks/use-chat";
import { cn } from "@/lib/utils";

interface ChatMessageListProps {
  messages: ChatMessage[];
}

export function ChatMessageList({ messages }: ChatMessageListProps) {
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
    <div className="flex h-full flex-col gap-4 overflow-y-auto px-4 py-3">
      {messages.map((message) => (
        <div
          key={message.id}
          className={cn(
            "flex w-full flex-col gap-1",
            message.role === "user" ? "items-end" : "items-start",
          )}
        >
          <div
            className={cn(
              "max-w-[80%] rounded-2xl px-4 py-2 text-sm shadow-sm",
              message.role === "user"
                ? "bg-primary text-primary-foreground"
                : "bg-card text-card-foreground",
            )}
          >
            {message.content}
          </div>

          {message.role === "assistant" &&
            message.sources &&
            message.sources.length > 0 && (
              <div className="mt-1 max-w-[80%] rounded-md bg-background/80 px-3 py-2 text-[11px] text-muted-foreground ring-1 ring-border">
                <div className="mb-1 font-medium">Fontes usadas:</div>
                <ul className="space-y-1">
                  {message.sources.map((source) => (
                    <li key={`${source.documentId}-${source.documentName}`}>
                      <span className="font-semibold">
                        {source.documentName}
                      </span>
                      {typeof source.score === "number" && (
                        <span className="ml-1 text-[10px] opacity-70">
                          (relevância {(source.score * 100).toFixed(0)}%)
                        </span>
                      )}
                      {source.chunkPreview && (
                        <div className="mt-0.5 line-clamp-2 text-[11px] italic">
                          “{source.chunkPreview}”
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
        </div>
      ))}
    </div>
  );
}
