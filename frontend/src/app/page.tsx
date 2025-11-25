// src/app/page.tsx
import { redirect } from "next/navigation";
// aqui você vai puxar sessão/cookie do jeito que escolher
// ex: import { getCurrentUser } from '@/shared/auth/getCurrentUser';

async function getCurrentUser() {
  // TODO: implementar com NextAuth, JWT, ou o que vocês escolherem
  return null;
}

export default async function RootPage() {
  const currentUser = await getCurrentUser();

  if (!currentUser) {
    redirect("/login");
  }

  redirect("/dashboard");
}
