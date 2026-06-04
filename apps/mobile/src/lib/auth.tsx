import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from 'react';

import { getStoredToken, storeToken } from './session';

type AuthContextValue = {
  bootstrapped: boolean;
  token: string | null;
  setToken: (token: string | null) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [bootstrapped, setBootstrapped] = useState(false);
  const [token, setTokenState] = useState<string | null>(null);

  useEffect(() => {
    getStoredToken()
      .then(setTokenState)
      .finally(() => setBootstrapped(true));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      bootstrapped,
      token,
      setToken: async (nextToken) => {
        await storeToken(nextToken);
        setTokenState(nextToken);
      },
    }),
    [bootstrapped, token],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}

