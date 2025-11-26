"use client";

import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";
import { CurrentUserProvider, useCurrentUser } from "@/hooks/use-current-user";
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';

function ProtectedContent({ children }: { children: ReactNode }) {
  const { user, isLoading } = useCurrentUser();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login");
    }
  }, [isLoading, user, router]);

  if (isLoading || (!user && typeof window !== "undefined")) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-neutral-500">Carregando painel...</p>
      </div>
    );
  }

  return (
   <div className="flex min-h-screen bg-slate-950 text-slate-50">
      <Sidebar />

      <div className="flex min-h-screen flex-1 flex-col bg-slate-50 text-slate-900">
        <Header />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
    );
}

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  return (
    <CurrentUserProvider>
      <ProtectedContent>{children}</ProtectedContent>
    </CurrentUserProvider>
  );
}
