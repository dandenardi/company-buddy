import { API_URL } from "./api";

const ACCESS_TOKEN_KEY = "access_token"; // mesma chave usada no login/callback

export interface DocumentItem {
  id: number;
  original_filename: string;
  content_type: string;
  status: "uploaded" | "processing" | "processed" | "failed";
  created_at: string;
}

function getAuthHeaders(): Record<string, string> {
  const token = typeof window !== "undefined"
    ? localStorage.getItem(ACCESS_TOKEN_KEY)
    : null;

  return token
    ? {
        Authorization: `Bearer ${token}`,
      }
    : {};
}

export async function apiListDocuments(): Promise<DocumentItem[]> {
  const res = await fetch(`${API_URL}/documents/`, {
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
  });

  if (!res.ok) {
    throw new Error("Erro ao buscar documentos.");
  }

  return res.json();
}

export async function apiUploadDocument(file: File): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append("file", file);

  const headers: HeadersInit = {
    ...getAuthHeaders(),
  };

  const res = await fetch(`${API_URL}/documents/upload`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    let message = "Erro ao enviar documento.";
    try {
      const data = await res.json();
      if (data?.detail) message = data.detail;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  return res.json();
}
