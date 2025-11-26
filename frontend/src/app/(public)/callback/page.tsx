"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get("token");
    
    if (token) {
      localStorage.setItem("access_token", token);
      router.replace("/dashboard"); // manda pro dashboard
    } else {
      router.replace("/login"); // ou mostra erro
    }
  }, [router, searchParams]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-50">
      <p>Finalizando login com Google...</p>
    </div>
  );
}
