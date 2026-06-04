import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';

export default function OperationsScreen() {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  const customersQuery = useQuery({
    queryKey: ['customers', token],
    queryFn: () => api.customers(token ?? ''),
    enabled: Boolean(token),
  });
  const jobsQuery = useQuery({
    queryKey: ['jobs', token],
    queryFn: () => api.jobs(token ?? ''),
    enabled: Boolean(token),
  });
  const invoicesQuery = useQuery({
    queryKey: ['invoices', token],
    queryFn: () => api.invoices(token ?? ''),
    enabled: Boolean(token),
  });
  const stockQuery = useQuery({
    queryKey: ['stock', token],
    queryFn: () => api.stock(token ?? ''),
    enabled: Boolean(token),
  });
  const voiceQuery = useQuery({
    queryKey: ['voice', token],
    queryFn: () => api.voiceSessions(token ?? ''),
    enabled: Boolean(token),
  });

  const createCustomer = useMutation({
    mutationFn: () =>
      api.createCustomer(token ?? '', {
        name: 'Sarah Customer',
        phone: '07700 900333',
        address: '10 High Street',
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['customers', token] }),
  });

  const createJob = useMutation({
    mutationFn: () =>
      api.createJob(token ?? '', {
        customer_id: customersQuery.data?.[0]?.id,
        title: 'Replace kitchen tap',
        description: 'Created from the mobile operations tab.',
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs', token] }),
  });

  const createInvoice = useMutation({
    mutationFn: () =>
      api.createInvoice(token ?? '', {
        customer_id: customersQuery.data?.[0]?.id,
        job_id: jobsQuery.data?.[0]?.id,
        amount_minor: 12500,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices', token] });
      queryClient.invalidateQueries({ queryKey: ['messages', token] });
    },
  });

  const createStock = useMutation({
    mutationFn: () =>
      api.createStock(token ?? '', {
        name: '15mm copper pipe',
        sku: `PIPE-${Date.now()}`,
        quantity: 12,
        reorder_level: 4,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['stock', token] }),
  });

  const createReceipt = useMutation({
    mutationFn: () =>
      api.createReceipt(token ?? '', {
        filename: 'receipt.jpg',
        job_id: jobsQuery.data?.[0]?.id,
        raw_text: 'Builders Merchant copper pipe 25.00',
        amount_minor: 2500,
      }),
  });

  if (!token) {
    return (
      <SafeAreaView style={styles.screen}>
        <View style={styles.content}>
          <Text style={styles.title}>Operations</Text>
          <Text style={styles.subtle}>Sign in on the dashboard to use jobs, invoices, stock, OCR, and voice.</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView contentContainerStyle={styles.content}>
        <View>
          <Text style={styles.kicker}>Operations</Text>
          <Text style={styles.title}>Jobs, money, materials, voice.</Text>
          <Text style={styles.subtle}>
            The v2 and v3 surfaces are wired to the same backend contracts as the missed-call wedge.
          </Text>
        </View>

        <View style={styles.grid}>
          <ActionPanel
            title="Customers"
            metric={String(customersQuery.data?.length ?? 0)}
            action="Create demo customer"
            onPress={() => createCustomer.mutate()}
            loading={createCustomer.isPending}
            rows={(customersQuery.data ?? []).slice(0, 3).map((customer) => `${customer.name ?? 'Customer'} - ${customer.phone}`)}
          />
          <ActionPanel
            title="Jobs"
            metric={String(jobsQuery.data?.length ?? 0)}
            action="Create job"
            onPress={() => createJob.mutate()}
            loading={createJob.isPending}
            rows={(jobsQuery.data ?? []).slice(0, 3).map((job) => `${job.title} - ${job.status}`)}
          />
          <ActionPanel
            title="Invoices"
            metric={String(invoicesQuery.data?.length ?? 0)}
            action="Create SumUp invoice"
            onPress={() => createInvoice.mutate()}
            loading={createInvoice.isPending}
            rows={(invoicesQuery.data ?? []).slice(0, 3).map((invoice) => `${invoice.number} - ${invoice.status}`)}
          />
          <ActionPanel
            title="Stock"
            metric={String(stockQuery.data?.length ?? 0)}
            action="Add stock item"
            onPress={() => createStock.mutate()}
            loading={createStock.isPending}
            rows={(stockQuery.data ?? []).slice(0, 3).map((item) => `${item.name} - ${item.quantity} in van`)}
          />
          <ActionPanel
            title="Receipt OCR"
            metric={createReceipt.data?.status ?? 'Ready'}
            action="Process receipt"
            onPress={() => createReceipt.mutate()}
            loading={createReceipt.isPending}
            rows={createReceipt.data ? [`Receipt ${createReceipt.data.receipt_upload_id.slice(0, 8)} processed`] : []}
          />
          <ActionPanel
            title="Voice AI"
            metric={String(voiceQuery.data?.length ?? 0)}
            action="Refresh sessions"
            onPress={() => queryClient.invalidateQueries({ queryKey: ['voice', token] })}
            rows={(voiceQuery.data ?? []).slice(0, 3).map((session) => `${session.call_id} - ${session.status}`)}
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function ActionPanel({
  title,
  metric,
  action,
  loading,
  rows,
  onPress,
}: {
  title: string;
  metric: string;
  action: string;
  loading?: boolean;
  rows: string[];
  onPress: () => void;
}) {
  return (
    <View style={styles.panel}>
      <View style={styles.panelHeader}>
        <Text style={styles.panelTitle}>{title}</Text>
        <Text style={styles.metric}>{metric}</Text>
      </View>
      <Pressable style={[styles.button, loading && styles.disabled]} disabled={loading} onPress={onPress}>
        <Text style={styles.buttonText}>{loading ? 'Working...' : action}</Text>
      </Pressable>
      {rows.length === 0 ? (
        <Text style={styles.subtle}>No records yet</Text>
      ) : (
        rows.map((row) => (
          <Text key={row} style={styles.row} numberOfLines={2}>
            {row}
          </Text>
        ))
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#f6f7f9',
  },
  content: {
    padding: 18,
    paddingTop: Platform.OS === 'web' ? 86 : 18,
    gap: 16,
    maxWidth: 980,
    width: '100%',
    alignSelf: 'center',
  },
  kicker: {
    color: '#007a61',
    fontWeight: '800',
    fontSize: 14,
    textTransform: 'uppercase',
  },
  title: {
    color: '#17202a',
    fontSize: 28,
    fontWeight: '800',
    lineHeight: 34,
  },
  subtle: {
    color: '#596674',
    fontSize: 14,
    lineHeight: 20,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  panel: {
    flexGrow: 1,
    flexBasis: 260,
    backgroundColor: '#ffffff',
    borderRadius: 8,
    padding: 16,
    gap: 12,
    borderWidth: 1,
    borderColor: '#e2e6ea',
    minHeight: 190,
  },
  panelHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  panelTitle: {
    color: '#17202a',
    fontWeight: '800',
    fontSize: 18,
  },
  metric: {
    color: '#007a61',
    fontWeight: '900',
    fontSize: 18,
  },
  button: {
    backgroundColor: '#007a61',
    minHeight: 44,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 12,
  },
  buttonText: {
    color: '#ffffff',
    fontWeight: '800',
  },
  disabled: {
    opacity: 0.6,
  },
  row: {
    borderTopWidth: 1,
    borderTopColor: '#edf0f3',
    paddingTop: 10,
    color: '#42505f',
    lineHeight: 19,
  },
});
