"use client";

import { useCurrentUser } from "@/hooks/use-current-user";
import { logout } from "@/lib/auth";
import { Skeleton } from "../ui/Skeleleton";
import { LogOut, User, Bell } from "lucide-react";

export function Header() {
  const { user, isLoading } = useCurrentUser();

  if (isLoading) {
    return (
      <header className="flex h-16 items-center justify-between border-b border-border bg-card px-6">
        <div className="space-y-2">
          <Skeleton className="h-5 w-40" />
        </div>
        <Skeleton className="h-9 w-9 rounded-full" />
      </header>
    );
  }

  if (!user) {
    return (
      <header className="flex h-16 items-center border-b border-border bg-destructive/10 px-6 text-sm text-destructive">
        Usuário não autenticado
      </header>
    );
  }

  const displayName = user.full_name ?? user.email;
  const tenantName = user.tenant?.name;

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-card px-6 shadow-sm">
      <div>
        <h1 className="text-xl font-semibold text-foreground">
          Olá, {displayName?.split(" ")[0]} <span className="text-2xl">👋</span>
        </h1>
      </div>

      <div className="flex items-center gap-4">
        <button className="relative rounded-full p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors">
          <Bell className="h-5 w-5" />
          <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-destructive ring-2 ring-card" />
        </button>

        <div className="h-6 w-px bg-border" />

        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-base font-medium text-primary ring-2 ring-background">
            {displayName?.[0]?.toUpperCase()}
          </div>

          <button
            type="button"
            onClick={logout}
            className="group flex items-center gap-2 rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-destructive hover:text-destructive-foreground hover:border-destructive"
          >
            <LogOut className="h-4 w-4" />
            <span>Sair</span>
          </button>
        </div>
      </div>
    </header>
  );
}
