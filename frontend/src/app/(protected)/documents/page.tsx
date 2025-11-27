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

  function getStatusLabel(status: DocumentItem["status"]) {
    switch (status) {
      case "uploaded":
        return "Enviado";
      case "processing":
        return "Processando";
      case "processed":
        return "Processado";
      case "failed":
        return "Falhou";
      default:
        return status;
    }
  }

  function getStatusClassName(status: DocumentItem["status"]) {
    switch (status) {
      case "uploaded":
        return "bg-slate-100 text-slate-700";
      case "processing":
        return "bg-indigo-100 text-indigo-700";
      case "processed":
        return "bg-emerald-100 text-emerald-700";
      case "failed":
        return "bg-red-100 text-red-700";
      default:
        return "bg-slate-100 text-slate-700";
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

  if (documents.length === 0) {
    return <DocumentsEmptyState onClickUpload={() => {}} />;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Meus Documentos</h1>
          <p className="text-sm text-slate-600">
            Envie PDFs ou arquivos DOCX para o Company Buddy aprender sobre a
            sua empresa.
          </p>
        </div>

        <label className="inline-flex cursor-pointer items-center rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50">
          <input
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
            onChange={handleFileChange}
            disabled={isUploading}
          />
          {isUploading ? "Enviando..." : "Enviar documento"}
        </label>
      </div>

      {errorMessage && (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {errorMessage}
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-slate-500">Carregando documentos...</p>
      ) : documents.length === 0 ? (
        <p className="text-sm text-slate-500">
          Nenhum documento enviado ainda. Comece enviando um PDF ou DOCX.
        </p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  Arquivo
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  Status
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  Tipo
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-600">
                  Enviado em
                </th>
                <th className="px-4 py-2 text-right font-medium text-slate-600">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td className="px-4 py-2">{doc.original_filename}</td>

                  <td className="px-4 py-2">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${getStatusClassName(
                        doc.status,
                      )}`}
                    >
                      {getStatusLabel(doc.status)}
                    </span>
                  </td>

                  <td className="px-4 py-2 text-slate-500">
                    {doc.content_type}
                  </td>

                  <td className="px-4 py-2 text-slate-500">
                    {new Date(doc.created_at).toLocaleString("pt-BR")}
                  </td>

                  <td className="px-4 py-2 text-right">
                    <div className="flex justify-end gap-2">
                      {doc.status === "failed" && (
                        <button
                          onClick={() => handleRetryDocument(doc.id)}
                          disabled={actionLoadingId === doc.id}
                          className="rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-xs font-medium text-amber-800 hover:bg-amber-100 disabled:opacity-50"
                        >
                          {actionLoadingId === doc.id
                            ? "Reenfileirando..."
                            : "Tentar novamente"}
                        </button>
                      )}

                      <button
                        onClick={() => handleDeleteDocument(doc.id)}
                        disabled={actionLoadingId === doc.id}
                        className="rounded-md border border-red-200 bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100 disabled:opacity-50"
                      >
                        {actionLoadingId === doc.id
                          ? "Removendo..."
                          : "Remover"}
                      </button>

                      <button
                        onClick={() =>
                          handleDownloadDocument(doc.id, doc.original_filename)
                        }
                        disabled={actionLoadingId === doc.id}
                        className="rounded-md border border-blue-200 bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50"
                      >
                        {actionLoadingId === doc.id ? "Baixando..." : "Baixar"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
