"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCurrentUser } from "@/hooks/use-current-user";
import {
  LayoutDashboard,
  FileText,
  MessageSquare,
  Settings,
  LogOut,
} from "lucide-react";
import { logout } from "@/lib/auth";

const navigationItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Meus Documentos", icon: FileText },
  { href: "/chat", label: "Chat Interno", icon: MessageSquare },
  { href: "/settings", label: "Configurações", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useCurrentUser();

  const tenantName = user?.tenant?.name ?? "Minha Empresa";

  const initialsSource = user?.full_name ?? user?.email ?? tenantName;
  const userInitials = initialsSource
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <aside className="flex h-screen w-72 flex-col border-r border-border bg-card text-card-foreground">
      {/* Header do Sidebar */}
      <div className="p-6">
        <div className="flex items-center gap-3 rounded-lg bg-primary/10 p-3 text-primary">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground font-bold shadow-sm">
            CB
          </div>
          <div className="flex flex-col overflow-hidden">
            <span className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
              Company Buddy
            </span>
            <span className="truncate text-base font-semibold">
              {tenantName}
            </span>
          </div>
        </div>
      </div>

      {/* Navegação principal */}
      <nav className="flex-1 space-y-1 px-4">
        {navigationItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));

          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "group flex items-center gap-3 rounded-md px-3 py-2.5 text-base font-medium transition-all duration-200",
                isActive
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              ].join(" ")}
            >
              <Icon
                className={`h-5 w-5 ${isActive ? "text-primary-foreground" : "text-muted-foreground group-hover:text-accent-foreground"}`}
              />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Rodapé com usuário */}
      <div className="border-t border-border p-4">
        <div className="flex items-center gap-3 rounded-lg bg-accent/50 p-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary ring-2 ring-background">
            {userInitials}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-base font-medium text-foreground">
              {user?.full_name ?? user?.email?.split("@")[0] ?? "Usuário"}
            </p>
            <p className="truncate text-sm text-muted-foreground">
              {user?.email ?? "sem-email@companybuddy.ai"}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
