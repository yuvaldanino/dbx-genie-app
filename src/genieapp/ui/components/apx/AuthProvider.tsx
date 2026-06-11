/**
 * AuthProvider — wraps the app with user context from GET /api/users/me.
 * Provides user info, loading state, and a context hook.
 */

import { createContext, useContext, useEffect, type ReactNode } from "react";
import { useCurrentUser, wakeWarehouse, type UserOut } from "@/lib/api";

interface AuthContextValue {
  user: UserOut | undefined;
  isLoading: boolean;
  isAnonymous: boolean;
}

const AuthContext = createContext<AuthContextValue>({
  user: undefined,
  isLoading: true,
  isAnonymous: true,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const { data: user, isLoading } = useCurrentUser();
  const isAnonymous = !user || user.user_id === "anonymous";

  // Warm the SQL warehouse the moment anyone opens the app — by the time the
  // first question is typed, the 1-3 min cold start is already underway.
  useEffect(() => {
    void wakeWarehouse();
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, isAnonymous }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
