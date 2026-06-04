import { DarkTheme, DefaultTheme, ThemeProvider } from 'expo-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useColorScheme } from 'react-native';

import AppTabs from '@/components/app-tabs';
import { AuthProvider } from '@/lib/auth';

const queryClient = new QueryClient();

export default function TabLayout() {
  const colorScheme = useColorScheme();
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
          <AppTabs />
        </ThemeProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
