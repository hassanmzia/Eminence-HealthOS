import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import {
  type User,
  type UserPermissions,
  login as apiLogin,
  logout as apiLogout,
  getCurrentUser,
  getStoredUser,
  getStoredPermissions,
  isAuthenticated as checkAuth,
} from "../lib/authApi";

interface AuthContextType {
  user: User | null;
  permissions: UserPermissions | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(getStoredUser);
  const [permissions, setPermissions] = useState<UserPermissions | null>(getStoredPermissions);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user && checkAuth();

  // Refresh user data from server
  const refreshUser = useCallback(async () => {
    if (!checkAuth()) {
      setUser(null);
      setPermissions(null);
      return;
    }

    try {
      const data = await getCurrentUser();
      setUser(data.user);
      setPermissions(data.permissions);
      localStorage.setItem("user", JSON.stringify(data.user));
      localStorage.setItem("permissions", JSON.stringify(data.permissions));
    } catch (error) {
      // Token invalid, clear auth state
      setUser(null);
      setPermissions(null);
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      localStorage.removeItem("permissions");
    }
  }, []);

  // Check auth on mount
  useEffect(() => {
    const initAuth = async () => {
      if (checkAuth()) {
        await refreshUser();
      }
      setIsLoading(false);
    };
    initAuth();
  }, [refreshUser]);

  const login = async (email: string, password: string) => {
    const response = await apiLogin(email, password);
    setUser(response.user);
    setPermissions(response.permissions);
  };

  const logout = async () => {
    await apiLogout();
    setUser(null);
    setPermissions(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        permissions,
        isAuthenticated,
        isLoading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

// Hook to check specific permission
export function usePermission(permission: keyof UserPermissions): boolean {
  const { permissions } = useAuth();
  return permissions?.[permission] ?? false;
}

// Hook to check if user has any of the specified roles
export function useHasRole(...roles: string[]): boolean {
  const { user } = useAuth();
  return user ? roles.includes(user.role) : false;
}
