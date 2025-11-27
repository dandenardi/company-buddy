"use client";

import { useCurrentUser } from "@/hooks/use-current-user";
import { logout } from "@/lib/auth";
import { Skeleton } from "../ui/Skeleleton";

export function Header() {
  const { user, isLoading } = useCurrentUser();

  if (isLoading) {
    return (
      <header className="flex items-center justify-between p-4 border-b border-border bg-background">
        <div className="space-y-2">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Skeleton className="h-9 w-9 rounded-full" />
      </header>
    );
  }

  if (!user) {
    return (
      <header className="p-4 border-b border-border text-sm text-red-500 bg-background">
        Usuário não autenticado
      </header>
    );
  }

  const displayName = user.full_name ?? user.email;
  const tenantName = user.tenant?.name;
  const tenantSlug = user.tenant?.slug;

  return (
    <header className="flex items-center justify-between p-4 border-b border-border bg-background">
      <div>
        <h1 className="text-xl font-semibold">Olá, {displayName} 👋</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Empresa: <span className="font-medium">{tenantName}</span>
          {tenantSlug && (
            <span className="text-muted-foreground/70"> ({tenantSlug})</span>
          )}
        </p>
      </div>

      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-full bg-muted flex items-center justify-center text-sm font-medium">
          {displayName?.[0]?.toUpperCase()}
        </div>
        <button
          type="button"
          onClick={logout}
          className="text-xs rounded-md border border-border px-3 py-1.5 text-foreground hover:bg-muted"
        >
          Sair
        </button>
      </div>
    </header>
  );
}
