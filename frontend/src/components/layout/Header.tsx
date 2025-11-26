"use client";

import { useCurrentUser } from "@/hooks/use-current-user";

export function Header() {
  const { user, isLoading } = useCurrentUser();

  if (isLoading) {
    return (
      <header className="p-4 border-b border-neutral-200 text-sm text-neutral-500">
        Carregando usuário...
      </header>
    );
  }

  if (!user) {
    // Em teoria, o layout já teria redirecionado,
    // então aqui é só um fallback defensivo.
    return (
      <header className="p-4 border-b border-neutral-200 text-sm text-red-500">
        Usuário não autenticado
      </header>
    );
  }

  const displayName = user.full_name ?? user.email;
  const tenantName = user.tenant?.name;
  const tenantSlug = user.tenant?.slug;

  return (
    <header className="flex items-center justify-between p-4 border-b border-neutral-200 bg-white">
      <div>
        <h1 className="text-xl font-semibold">Olá, {displayName} 👋</h1>
        <p className="text-sm text-neutral-500 mt-1">
          Empresa: <span className="font-medium">{tenantName}</span>
          {tenantSlug && (
            <span className="text-neutral-400"> ({tenantSlug})</span>
          )}
        </p>
      </div>

      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-full bg-neutral-200 flex items-center justify-center text-sm font-medium">
          {displayName?.[0]?.toUpperCase()}
        </div>
      </div>
    </header>
  );
}
