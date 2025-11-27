"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { apiRegister } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    const formData = new FormData(event.currentTarget);
    const tenantName = formData.get("tenantName") as string;
    const fullName = (formData.get("fullName") as string) || null;
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;

    try {
      const data = await apiRegister(tenantName, fullName, email, password);

      // backend retorna LoginResponse (access_token)
      localStorage.setItem("access_token", data.access_token);
      router.replace("/dashboard");
    } catch (error: any) {
      setErrorMessage(error.message ?? "Erro inesperado ao criar conta.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md bg-white p-8 rounded-xl shadow">
        <h1 className="text-2xl font-semibold mb-6 text-center">
          Criar conta • CompanyBuddy
        </h1>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <input
            type="text"
            name="tenantName"
            placeholder="Nome da empresa"
            className="w-full p-3 rounded border"
            required
          />

          <input
            type="text"
            name="fullName"
            placeholder="Seu nome (opcional)"
            className="w-full p-3 rounded border"
          />

          <input
            type="email"
            name="email"
            placeholder="Email"
            className="w-full p-3 rounded border"
            required
          />

          <input
            type="password"
            name="password"
            placeholder="Senha"
            className="w-full p-3 rounded border"
            required
          />

          {errorMessage && (
            <p className="text-sm text-red-500">{errorMessage}</p>
          )}

          <button
            type="submit"
            className="w-full bg-blue-600 text-white p-3 rounded font-semibold disabled:opacity-60"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Criando conta..." : "Criar conta"}
          </button>
        </form>

        <div className="mt-4 text-center text-sm">
          Já tem conta?{" "}
          <a href="/login" className="text-blue-600 underline">
            Entrar
          </a>
        </div>
      </div>
    </div>
  );
}
