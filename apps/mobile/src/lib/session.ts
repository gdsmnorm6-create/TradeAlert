import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const TOKEN_KEY = 'tradealert.accessToken';

export async function getStoredToken(): Promise<string | null> {
  if (Platform.OS === 'web') {
    return globalThis.localStorage?.getItem(TOKEN_KEY) ?? null;
  }
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function storeToken(token: string | null): Promise<void> {
  if (Platform.OS === 'web') {
    if (token) {
      globalThis.localStorage?.setItem(TOKEN_KEY, token);
    } else {
      globalThis.localStorage?.removeItem(TOKEN_KEY);
    }
    return;
  }
  if (token) {
    await SecureStore.setItemAsync(TOKEN_KEY, token);
  } else {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  }
}

