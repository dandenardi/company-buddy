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
  const [documents, setDocuments] = useState<any[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);

    if (!accessToken) {
      router.replace("/login");
      return;
    }

    async function loadData() {
      if (!accessToken) return;

      try {
        const [meData, docsData] = await Promise.all([
          apiGetMe(accessToken),
          import("@/lib/api").then((mod) => mod.apiGetDocuments(accessToken)),
        ]);
        setMe(meData);
        // Sort by created_at desc just in case, and take top 5
        const sortedDocs = (docsData || []).sort(
          (a: any, b: any) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        );
        setDocuments(sortedDocs.slice(0, 5));
      } catch (error: any) {
        setErrorMessage(error.message ?? "Erro ao carregar dados.");
        // If it's an auth error, it might be handled by api.ts redirect, but good to be safe
        if (error.message?.includes("401")) {
          localStorage.removeItem(ACCESS_TOKEN_KEY);
          router.replace("/login");
        }
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, [router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-50">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="h-8 w-8 bg-indigo-500 rounded-full animate-bounce"></div>
          <p className="text-slate-400">Carregando seu ambiente...</p>
        </div>
      </div>
    );
  }

  if (!me) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-50">
        <div className="text-center">
          <p className="text-red-400 mb-4">
            {errorMessage ?? "Nenhum usuário carregado."}
          </p>
          <button
            onClick={() => router.replace("/login")}
            className="text-indigo-400 hover:text-indigo-300 underline"
          >
            Voltar para Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 p-6">
      <header className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Olá, {me.full_name || me.email}
          </h1>
          <p className="text-slate-400">
            Bem-vindo ao workspace{" "}
            <span className="text-indigo-400 font-medium">
              {me.tenant.name}
            </span>
          </p>
        </div>
        <button
          onClick={() => router.push("/documents")}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2 text-sm font-medium"
        >
          <span>+</span> Novo Documento
        </button>
      </header>

      <main className="grid gap-6 lg:grid-cols-3">
        {/* Recent Documents Section */}
        <section className="lg:col-span-2 bg-slate-900/50 border border-slate-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-white">
              Documentos Recentes
            </h2>
            <button
              onClick={() => router.push("/documents")}
              className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              Ver todos
            </button>
          </div>

          {documents.length === 0 ? (
            <div className="text-center py-12 border-2 border-dashed border-slate-800 rounded-lg">
              <p className="text-slate-400 mb-2">Nenhum documento ainda</p>
              <p className="text-sm text-slate-500">
                Faça upload do seu primeiro arquivo para começar
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-slate-800/50 hover:border-slate-700 transition-all"
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div className="h-8 w-8 rounded bg-slate-700 flex items-center justify-center flex-shrink-0 text-xs font-bold text-slate-400">
                      DOC
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-200 truncate">
                        {doc.original_filename}
                      </p>
                      <p className="text-xs text-slate-500">
                        {new Date(doc.created_at).toLocaleDateString("pt-BR")}
                      </p>
                    </div>
                  </div>
                  <div className="flex-shrink-0">
                    <span
                      className={`text-xs px-2 py-1 rounded-full font-medium ${
                        doc.status === "processed"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : doc.status === "failed"
                            ? "bg-red-500/10 text-red-400"
                            : "bg-amber-500/10 text-amber-400"
                      }`}
                    >
                      {doc.status === "processed"
                        ? "Pronto"
                        : doc.status === "failed"
                          ? "Falha"
                          : "Processando"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Quick Stats / Info Section */}
        <section className="space-y-6">
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">
              Status do Sistema
            </h2>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-400">Armazenamento</span>
                <span className="text-sm text-slate-200 font-medium">
                  -- / 1GB
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5">
                <div
                  className="bg-indigo-500 h-1.5 rounded-full"
                  style={{ width: "5%" }}
                ></div>
              </div>
              <div className="pt-4 border-t border-slate-800">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-400">Documentos</span>
                  <span className="text-sm text-slate-200 font-medium">
                    {documents.length} recentes
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-indigo-600 to-violet-600 rounded-xl p-6 text-white">
            <h3 className="font-bold text-lg mb-2">Dica Pro</h3>
            <p className="text-sm text-indigo-100 mb-4">
              Você pode fazer perguntas sobre múltiplos documentos de uma vez no
              chat.
            </p>
            <button className="bg-white/10 hover:bg-white/20 text-white text-sm px-4 py-2 rounded-lg transition-colors w-full font-medium">
              Ir para o Chat
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}
