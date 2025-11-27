"use client";

import { useEffect } from "react";
import { useChat } from "@/hooks/use-chat";
import { ChatMessageList } from "@/components/chat/ChatMessageList";
import { ChatInput } from "@/components/chat/ChatInput";

export default function ChatPage() {
  const { messages, isLoading, errorMessage, sendMessage } = useChat();

  useEffect(() => {
    if (errorMessage) {
      // Aqui você pode trocar por um toast global, se já tiver.
      console.error("Erro no chat:", errorMessage);
    }
  }, [errorMessage]);

  return (
    <div className="flex h-full flex-col">
      {/* Header simples, se o layout principal não já tiver um */}
      <div className="flex items-center justify-between border-b px-6 py-3">
        <div>
          <h1 className="text-lg font-semibold">Chat com o Company Buddy</h1>
          <p className="text-xs text-muted-foreground">
            Pergunte qualquer coisa sobre os documentos deste tenant.
          </p>
        </div>
      </div>

      {/* Área central: lista de mensagens */}
      <div className="flex-1">
        <ChatMessageList messages={messages} />
      </div>

      {/* Erro (inline) */}
      {errorMessage && (
        <div className="px-4 py-2 text-xs text-red-500">{errorMessage}</div>
      )}

      {/* Input */}
      <ChatInput onSendMessage={sendMessage} isLoading={isLoading} />
    </div>
  );
}
