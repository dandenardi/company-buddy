"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCurrentUser } from "@/hooks/use-current-user";

const navigationItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/documents", label: "Meus Documentos" },
  { href: "/chat", label: "Chat Interno" },
  { href: "/settings", label: "Configurações" },
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
    <aside className="flex h-screen w-64 flex-col border-r border-slate-800 bg-slate-950 text-slate-50">
      {/* Topo colorido estilo Slack */}
      <div className="border-b border-slate-800 bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-white/15 text-sm font-semibold">
            {userInitials}
          </div>
          <div className="flex flex-col">
            <span className="text-xs uppercase tracking-wide text-white/70">
              Company Buddy
            </span>
            <span className="truncate text-sm font-semibold text-white">
              {tenantName}
            </span>
          </div>
        </div>
      </div>

      {/* Navegação principal */}
      <nav className="flex-1 space-y-1 p-3">
        {navigationItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));

          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-slate-800 text-slate-50"
                  : "text-slate-300 hover:bg-slate-900 hover:text-slate-50",
              ].join(" ")}
            >
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Rodapé com usuário */}
      <div className="border-t border-slate-800 p-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800 text-xs font-medium">
            {userInitials}
          </div>
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-slate-100">
              {user?.full_name ?? user?.email ?? "Usuário"}
            </p>
            <p className="truncate text-[11px] text-slate-400">
              {user?.email ?? "sem-email@companybuddy.ai"}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
