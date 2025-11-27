import { API_URL, handleJsonResponse } from "./api";
import { ACCESS_TOKEN_KEY } from "./auth";

export interface DocumentItem {
  id: number;
  original_filename: string;
  content_type: string;
  status: "uploaded" | "processing" | "processed" | "failed";
  created_at: string;
}

function getAuthHeaders(): Record<string, string> {
  const token =
    typeof window !== "undefined"
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

  return handleJsonResponse(res);
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
    let message = "Error uploading document.";
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

export async function apiDeleteDocument(id: number): Promise<void> {
  const headers: HeadersInit = {
    ...getAuthHeaders(),
  };

  const res = await fetch(`${API_URL}/documents/${id}`, {
    method: "DELETE",
    headers,
  });

  if (!res.ok) {
    let message = "Error deleting document.";
    try {
      const data = await res.json();
      if (data?.detail) message = data.detail;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
}

export async function apiRetryDocument(id: number): Promise<void> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...getAuthHeaders(),
  };

  const res = await fetch(`${API_URL}/documents/${id}/retry`, {
    method: "POST",
    headers,
  });

  if (!res.ok) {
    let message = "Error requeuing ingestion.";
    try {
      const data = await res.json();
      if (data?.detail) message = data.detail;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
}
