"use client";

interface DocumentsEmptyStateProps {
  onClickUpload?: () => void;
}

export function DocumentsEmptyState({
  onClickUpload,
}: DocumentsEmptyStateProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-4 text-center">
      <h2 className="text-sm font-semibold text-foreground">
        Nenhum documento enviado ainda
      </h2>
      <p className="text-xs text-muted-foreground max-w-sm">
        Envie PDFs ou documentos do Word com políticas, manuais e informações da
        sua empresa. O Company Buddy vai usar esses arquivos como base de
        conhecimento.
      </p>
      <button
        type="button"
        onClick={onClickUpload}
        className="mt-1 inline-flex items-center rounded-md bg-primary px-4 py-2 text-xs font-medium text-primary-foreground shadow-sm hover:opacity-90"
      >
        Enviar meu primeiro documento
      </button>
    </div>
  );
}
