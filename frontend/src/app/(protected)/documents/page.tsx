"use client";

import { useEffect, useState } from "react";
import {
  apiDeleteDocument,
  apiListDocuments,
  apiRetryDocument,
  apiUploadDocument,
  DocumentItem,
} from "@/lib/documents-api";
import { API_URL } from "@/lib/api";
import { ACCESS_TOKEN_KEY } from "@/lib/auth";
import { DocumentsSkeleton } from "@/components/documents/DocumentsSkeleton";
import { DocumentsEmptyState } from "@/components/documents/DocumentsEmptyState";
import {
  FileText,
  UploadCloud,
  Trash2,
  Download,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  File,
} from "lucide-react";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

  async function loadDocuments() {
    try {
      setIsLoading(true);
      setErrorMessage(null);
      const data = await apiListDocuments();
      setDocuments(data);
    } catch (error) {
      console.error(error);
      setErrorMessage("Não foi possível carregar os documentos.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setIsUploading(true);
      setErrorMessage(null);
      await apiUploadDocument(file);
      await loadDocuments();
      event.target.value = "";
    } catch (error: any) {
      console.error(error);
      setErrorMessage(error?.message ?? "Erro ao enviar documento.");
    } finally {
      setIsUploading(false);
    }
  }

  function getStatusConfig(status: DocumentItem["status"]) {
    switch (status) {
      case "uploaded":
        return {
          label: "Enviado",
          icon: Clock,
          className: "bg-secondary text-secondary-foreground",
        };
      case "processing":
        return {
          label: "Processando",
          icon: RefreshCw,
          className: "bg-indigo-100 text-indigo-700 animate-pulse",
        };
      case "processed":
        return {
          label: "Pronto",
          icon: CheckCircle2,
          className: "bg-emerald-100 text-emerald-700",
        };
      case "failed":
        return {
          label: "Falhou",
          icon: AlertCircle,
          className: "bg-red-100 text-red-700",
        };
      default:
        return {
          label: status,
          icon: File,
          className: "bg-secondary text-secondary-foreground",
        };
    }
  }

  async function handleRetryDocument(id: number) {
    try {
      setActionLoadingId(id);
      setErrorMessage(null);
      await apiRetryDocument(id);
      await loadDocuments();
    } catch (error: any) {
      console.error(error);
      setErrorMessage(error?.message ?? "Erro ao reenviar para ingestão.");
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleDownloadDocument(
    documentId: number,
    documentName: string,
  ) {
    try {
      const accessToken =
        typeof window !== "undefined"
          ? window.localStorage.getItem(ACCESS_TOKEN_KEY)
          : null;

      if (!accessToken) {
        alert("Sessão expirada. Faça login novamente.");
        return;
      }

      const response = await fetch(
        `${API_URL}/documents/${documentId}/download`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        },
      );

      if (!response.ok) {
        let errorMessage = "Falha ao baixar o documento.";
        try {
          const data = await response.json();
          if (data?.detail) {
            errorMessage = data.detail;
          }
        } catch {
          // ignora, usa texto padrão
        }
        alert(errorMessage);
        return;
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = downloadUrl;
      link.download = documentName || "documento";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error("Erro ao baixar documento:", error);
      alert("Erro inesperado ao baixar o documento.");
    }
  }

  async function handleDeleteDocument(id: number) {
    if (!confirm("Tem certeza que deseja remover este documento?")) return;

    try {
      setActionLoadingId(id);
      setErrorMessage(null);
      await apiDeleteDocument(id);
      await loadDocuments();
    } catch (error: any) {
      console.error(error);
      setErrorMessage(error?.message ?? "Erro ao excluir documento.");
    } finally {
      setActionLoadingId(null);
    }
  }

  if (isLoading) {
    return <DocumentsSkeleton />;
  }

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Meus Documentos
          </h1>
          <p className="text-muted-foreground mt-1">
            Gerencie os arquivos que o Company Buddy usa para aprender.
          </p>
        </div>

        <label
          className={`
          group relative inline-flex cursor-pointer items-center justify-center gap-2 rounded-lg 
          bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-sm 
          transition-all hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2
          ${isUploading ? "opacity-70 cursor-not-allowed" : ""}
        `}
        >
          <input
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
            onChange={handleFileChange}
            disabled={isUploading}
          />
          {isUploading ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin" />
              <span>Enviando...</span>
            </>
          ) : (
            <>
              <UploadCloud className="h-4 w-4" />
              <span>Novo Documento</span>
            </>
          )}
        </label>
      </div>

      {errorMessage && (
        <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          {errorMessage}
        </div>
      )}

      {documents.length === 0 ? (
        <DocumentsEmptyState onClickUpload={() => {}} />
      ) : (
        <div className="grid gap-4">
          {documents.map((doc) => {
            const statusConfig = getStatusConfig(doc.status);
            const StatusIcon = statusConfig.icon;

            return (
              <div
                key={doc.id}
                className="group flex items-center justify-between rounded-xl border border-border bg-card p-4 shadow-sm transition-all hover:shadow-md hover:border-primary/20"
              >
                <div className="flex items-center gap-4 min-w-0">
                  <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg bg-secondary text-muted-foreground">
                    <FileText className="h-6 w-6" />
                  </div>

                  <div className="min-w-0 flex-1">
                    <h3
                      className="truncate font-medium text-foreground"
                      title={doc.original_filename}
                    >
                      {doc.original_filename}
                    </h3>
                    <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                      <span>
                        {new Date(doc.created_at).toLocaleDateString("pt-BR")}
                      </span>
                      <span>•</span>
                      <span>
                        {doc.content_type?.split("/")[1]?.toUpperCase() ??
                          "FILE"}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4 md:gap-8">
                  <div
                    className={`flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${statusConfig.className}`}
                  >
                    <StatusIcon className="h-3.5 w-3.5" />
                    {statusConfig.label}
                  </div>

                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {doc.status === "failed" && (
                      <button
                        onClick={() => handleRetryDocument(doc.id)}
                        disabled={actionLoadingId === doc.id}
                        className="rounded-md p-2 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                        title="Tentar novamente"
                      >
                        <RefreshCw
                          className={`h-4 w-4 ${actionLoadingId === doc.id ? "animate-spin" : ""}`}
                        />
                      </button>
                    )}

                    <button
                      onClick={() =>
                        handleDownloadDocument(doc.id, doc.original_filename)
                      }
                      disabled={actionLoadingId === doc.id}
                      className="rounded-md p-2 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                      title="Baixar"
                    >
                      <Download className="h-4 w-4" />
                    </button>

                    <button
                      onClick={() => handleDeleteDocument(doc.id)}
                      disabled={actionLoadingId === doc.id}
                      className="rounded-md p-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                      title="Excluir"
                    >
                      {actionLoadingId === doc.id ? (
                        <RefreshCw className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
