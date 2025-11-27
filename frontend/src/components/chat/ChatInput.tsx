"use client";

import { FormEvent, useState } from "react";

interface ChatInputProps {
  onSendMessage: (message: string) => Promise<void> | void;
  isLoading?: boolean;
}

export function ChatInput({ onSendMessage, isLoading }: ChatInputProps) {
  const [currentMessage, setCurrentMessage] = useState<string>("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedMessage = currentMessage.trim();
    if (!trimmedMessage || isLoading) {
      return;
    }

    await onSendMessage(trimmedMessage);
    setCurrentMessage("");
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center gap-2 border-t border-border bg-background px-4 py-3"
    >
      <textarea
        rows={1}
        value={currentMessage}
        onChange={(event) => setCurrentMessage(event.target.value)}
        placeholder="Faça uma pergunta sobre os seus documentos..."
        className="
          flex-1 resize-none rounded-xl border border-border
          bg-card text-foreground
          placeholder:text-muted-foreground
          px-3 py-2 text-sm
          outline-none ring-offset-background
          focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1
        "
      />
      <button
        type="submit"
        disabled={isLoading || !currentMessage.trim()}
        className="
          inline-flex items-center rounded-xl
          bg-primary px-4 py-2 text-sm font-medium text-primary-foreground
          shadow-sm
          disabled:cursor-not-allowed disabled:opacity-60
        "
      >
        {isLoading ? "Perguntando..." : "Enviar"}
      </button>
    </form>
  );
}
