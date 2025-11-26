"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGetMe } from "@/lib/api";

const ACCESS_TOKEN_KEY = "access_token";

interface TenantInfo {
  id: number;
  name: string;
  slug: string;
}

interface MeResponse {
  id: number;
  email: string;
  full_name?: string | null;
  tenant: TenantInfo;
}

export default function AppDashboardPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [me, setMe] = useState<MeResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    
    const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    
    if (!accessToken) {
      router.replace("/login");
      return;
    }

    async function loadMe() {
      if (!accessToken) return;
      
      try {
        const data = await apiGetMe(accessToken);
        setMe(data);
      } catch (error: any) {
        setErrorMessage(error.message ?? "Erro ao carregar dados.");
        // token inválido/expirado → limpa e manda pro login
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        router.replace("/login");
      } finally {
        setIsLoading(false);
      }
    }

    loadMe();
  }, [router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-50">
        <p>Carregando seu ambiente...</p>
      </div>
    );
  }

  if (!me) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-50">
       {errorMessage ?? "Nenhum usuário carregado."}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      

      <main className="p-6 grid gap-6 lg:grid-cols-3">
        <section className="lg:col-span-2 bg-slate-900 rounded-xl p-4">
          <h2 className="text-lg font-medium mb-2">Chat interno (em breve)</h2>
          <p className="text-sm text-slate-300">
            Aqui vai ficar o chat com o mini-RAG respondendo com base nos
            documentos da empresa <span className="font-semibold">{me.tenant.name}</span>.
          </p>
        </section>

        <section className="bg-slate-900 rounded-xl p-4">
          <h2 className="text-lg font-medium mb-2">Meus documentos (em breve)</h2>
          <p className="text-sm text-slate-300">
            Aqui você vai poder enviar PDFs, Word e acompanhar o status da
            ingestão.
          </p>
        </section>
      </main>
    </div>
  );
}
