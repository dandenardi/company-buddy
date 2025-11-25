// frontend/lib/api.ts
export const API_URL = "http://localhost:8000/api/v1";

async function handleJsonResponse(res: Response) {
  if (!res.ok) {
    try {
      const data = await res.json();
      if (data?.detail) {
        throw new Error(data.detail);
      }
    } catch {
      
    }
    throw new Error("Error while communicating with the API.");
  }

  return res.json();
}

export async function apiLogin(email: string, password: string) {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  return handleJsonResponse(res);
}

export async function apiRegister(
  tenantName: string,
  fullName: string | null,
  email: string,
  password: string
) {
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      tenant_name: tenantName,
      full_name: fullName,
      email,
      password,
    }),
  });

  return handleJsonResponse(res);
}

export const GOOGLE_LOGIN_URL = `${API_URL}/auth/login/google`;

export async function apiGetMe(accessToken: string) {
  const res = await fetch(`${API_URL}/auth/me`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!res.ok) {
    let message = "Error while fetching user data.";
    try {
      const data = await res.json();
      if (data?.detail) message = data.detail;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  return res.json();
}