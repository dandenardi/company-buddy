"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { apiGetMe } from "@/lib/api";

const ACCESS_TOKEN_KEY = "access_token"; 

export interface TenantInfo {
  id: string;
  name: string;
  slug: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string | null;
  tenant: TenantInfo;
}

interface CurrentUserContextValue {
  user: CurrentUser | null;
  isLoading: boolean;
  error: string | null;
}

const CurrentUserContext = createContext<CurrentUserContextValue>({
  user: null,
  isLoading: true,
  error: null,
});

export function CurrentUserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadCurrentUser() {
      try {
        const accessTokenFromStorage = localStorage.getItem(ACCESS_TOKEN_KEY);

        if (!accessTokenFromStorage) {
          setUser(null);
          setError("NO_TOKEN");
          return;
        }

        const meResponse = await apiGetMe(accessTokenFromStorage);
        setUser(meResponse);
        setError(null);
      } catch (err) {
        console.error("Error while fetching /auth/me:", err);
        setUser(null);
        setError("FAILED_REQUEST");
      } finally {
        setIsLoading(false);
      }
    }

    loadCurrentUser();
  }, []);

  return (
    <CurrentUserContext.Provider value={{ user, isLoading, error }}>
      {children}
    </CurrentUserContext.Provider>
  );
}

export function useCurrentUser() {
  return useContext(CurrentUserContext);
}
