"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { apiLogin, GOOGLE_LOGIN_URL } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    const formData = new FormData(event.currentTarget);
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;

    try {
      const data = await apiLogin(email, password);

      // backend retorna { access_token: "..." }
      localStorage.setItem("access_token", data.access_token);
      router.replace("/dashboard");
    } catch (error: any) {
      setErrorMessage(error.message ?? "Erro inesperado ao fazer login.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleGoogleLogin() {
    window.location.href = GOOGLE_LOGIN_URL;
  }

  return (
    <div className="min-h-screen flex items-center justify-center ">
      <div className="w-full max-w-md p-8 rounded-xl shadow">
        <h1 className="text-2xl font-semibold mb-6 text-center">
          CompanyBuddy Login
        </h1>

        <form className="space-y-4" onSubmit={handleSubmit}>
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
            placeholder="Password"
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
            {isSubmitting ? "Entrando..." : "Sign in"}
          </button>
        </form>

        <div className="my-6 text-center text-gray-500">or</div>

        <div className="mt-4 flex flex-col gap-2">
          <button
            type="button"
            onClick={handleGoogleLogin}
            className="w-full rounded-md border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Continuar com Google
          </button>

          <div className="mt-4 text-center text-sm">
            Ainda não tem conta?{" "}
            <a href="/register" className="text-blue-600 underline">
              Cadastre-se
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
