import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { Linking, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { Customer, Job } from '@/lib/types';

const screwfixUrl = 'https://www.screwfix.com/login';

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

  const firstCustomer = customersQuery.data?.[0];
  const firstJob = jobsQuery.data?.[0];

  const createCustomer = useMutation({
    mutationFn: () =>
      api.createCustomer(token ?? '', {
        name: 'Sarah Customer',
        phone: '07700 900333',
        address: '10 High Street, Birmingham',
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['customers', token] }),
  });

  const createJob = useMutation({
    mutationFn: async () => {
      let customer = firstCustomer;
      if (!customer) {
        customer = await api.createCustomer(token ?? '', {
          name: 'Sarah Customer',
          phone: '07700 900333',
          address: '10 High Street, Birmingham',
        });
      }
      return api.createJob(token ?? '', {
        customer_id: customer.id,
        title: 'Replace kitchen tap',
        description: 'Customer wants photos attached for invoice and possible report.',
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers', token] });
      queryClient.invalidateQueries({ queryKey: ['jobs', token] });
    },
  });

  const createInvoice = useMutation({
    mutationFn: () =>
      api.createInvoice(token ?? '', {
        customer_id: firstCustomer?.id,
        job_id: firstJob?.id,
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
        filename: 'job-photo-receipt.jpg',
        job_id: firstJob?.id,
        raw_text: 'Screwfix copper pipe fittings 25.00',
        amount_minor: 2500,
      }),
  });

  if (!token) {
    return (
      <SafeAreaView style={styles.screen}>
        <View style={styles.content}>
          <Text style={styles.kicker}>Operations</Text>
          <Text style={styles.title}>Sign in first.</Text>
          <Text style={styles.subtle}>Jobs, invoices, photos, stock, and reports unlock after login.</Text>
        </View>
      </SafeAreaView>
    );
  }

  const customers = customersQuery.data ?? [];
  const jobs = jobsQuery.data ?? [];
  const invoices = invoicesQuery.data ?? [];
  const stock = stockQuery.data ?? [];
  const lowStock = stock.filter((item) => item.quantity <= item.reorder_level);

  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <Text style={styles.kicker}>Operations</Text>
          <Text style={styles.title}>Jobs, parts, photos, money.</Text>
          <Text style={styles.subtle}>
            The extra bits stay separated so the phone screen does not become a junk drawer.
          </Text>
        </View>

        <View style={styles.summaryBand}>
          <SummaryNumber label="Jobs" value={String(jobs.length)} />
          <SummaryNumber label="Invoices" value={String(invoices.length)} />
          <SummaryNumber label="Stock" value={String(stock.length)} />
          <SummaryNumber label="Low" value={String(lowStock.length)} />
        </View>

        <Section
          title="Jobs"
          detail="Customer, address, photos, notes, and invoice trail."
          actionLabel="Create test job"
          loading={createJob.isPending}
          onAction={() => createJob.mutate()}>
          {jobs.length === 0 ? (
            <Empty text="No jobs yet." />
          ) : (
            jobs.slice(0, 4).map((job) => {
              const customer = customers.find((item) => item.id === job.customer_id);
              return <JobRow key={job.id} job={job} customer={customer} />;
            })
          )}
        </Section>

        <Section
          title="Invoices and photos"
          detail="Take job photos, send SumUp links, and prepare an insurance report if needed."
          actionLabel="Create invoice"
          loading={createInvoice.isPending}
          onAction={() => createInvoice.mutate()}>
          <ActionStrip
            actions={[
              { label: 'Add photo note', onPress: () => createReceipt.mutate(), busy: createReceipt.isPending },
              { label: 'Insurance report', onPress: () => createReceipt.mutate(), busy: createReceipt.isPending },
            ]}
          />
          {invoices.length === 0 ? (
            <Empty text="No invoices yet." />
          ) : (
            invoices.slice(0, 4).map((invoice) => (
              <View key={invoice.id} style={styles.row}>
                <Text style={styles.rowTitle}>{invoice.number}</Text>
                <Text style={styles.rowDetail}>
                  {money(invoice.amount_minor, invoice.currency)} - {invoice.status}
                </Text>
              </View>
            ))
          )}
        </Section>

        <Section
          title="Van stock"
          detail="Keep the van count simple, then use Screwfix for the real basket and collection."
          actionLabel="Add stock item"
          loading={createStock.isPending}
          onAction={() => createStock.mutate()}>
          <ActionStrip actions={[{ label: 'Open Screwfix', onPress: () => Linking.openURL(screwfixUrl) }]} />
          {stock.length === 0 ? (
            <Empty text="No van stock yet." />
          ) : (
            stock.slice(0, 5).map((item) => (
              <View key={item.id} style={styles.row}>
                <Text style={styles.rowTitle}>{item.name}</Text>
                <Text style={styles.rowDetail}>
                  {item.quantity} in van - reorder at {item.reorder_level}
                </Text>
              </View>
            ))
          )}
        </Section>

        <Section
          title="Customers"
          detail="Addresses open straight into Google Maps."
          actionLabel="Create customer"
          loading={createCustomer.isPending}
          onAction={() => createCustomer.mutate()}>
          {customers.length === 0 ? (
            <Empty text="No customers yet." />
          ) : (
            customers.slice(0, 5).map((customer) => <CustomerRow key={customer.id} customer={customer} />)
          )}
        </Section>
      </ScrollView>
    </SafeAreaView>
  );
}

function Section({
  title,
  detail,
  actionLabel,
  loading,
  onAction,
  children,
}: {
  title: string;
  detail: string;
  actionLabel: string;
  loading?: boolean;
  onAction: () => void;
  children: ReactNode;
}) {
  return (
    <View style={styles.panel}>
      <View style={styles.sectionHeader}>
        <View style={styles.sectionTitleWrap}>
          <Text style={styles.panelTitle}>{title}</Text>
          <Text style={styles.subtle}>{detail}</Text>
        </View>
        <Pressable style={[styles.smallButton, loading && styles.disabled]} disabled={loading} onPress={onAction}>
          <Text style={styles.smallButtonText}>{loading ? 'Working' : actionLabel}</Text>
        </Pressable>
      </View>
      {children}
    </View>
  );
}

function ActionStrip({ actions }: { actions: { label: string; onPress: () => void; busy?: boolean }[] }) {
  return (
    <View style={styles.actionStrip}>
      {actions.map((action) => (
        <Pressable
          key={action.label}
          style={[styles.secondaryButton, action.busy && styles.disabled]}
          disabled={action.busy}
          onPress={action.onPress}>
          <Text style={styles.secondaryButtonText}>{action.busy ? 'Working' : action.label}</Text>
        </Pressable>
      ))}
    </View>
  );
}

function JobRow({ job, customer }: { job: Job; customer?: Customer }) {
  const address = customer?.address;
  return (
    <View style={styles.row}>
      <Text style={styles.rowTitle}>{job.title}</Text>
      <Text style={styles.rowDetail}>
        {customer?.name ?? 'Customer'} - {job.status}
      </Text>
      {address ? (
        <Pressable style={styles.linkButton} onPress={() => openMaps(address)}>
          <Text style={styles.linkButtonText}>Open address in Google Maps</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

function CustomerRow({ customer }: { customer: Customer }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowTitle}>{customer.name ?? 'Customer'}</Text>
      <Text style={styles.rowDetail}>{customer.phone}</Text>
      {customer.address ? (
        <Pressable style={styles.linkButton} onPress={() => openMaps(customer.address ?? '')}>
          <Text style={styles.linkButtonText}>{customer.address}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

function SummaryNumber({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.summaryItem}>
      <Text style={styles.summaryValue}>{value}</Text>
      <Text style={styles.summaryLabel}>{label}</Text>
    </View>
  );
}

function Empty({ text }: { text: string }) {
  return <Text style={styles.emptyText}>{text}</Text>;
}

function openMaps(address: string) {
  const query = encodeURIComponent(address);
  Linking.openURL(`https://www.google.com/maps/search/?api=1&query=${query}`);
}

function money(amountMinor: number, currency: string) {
  return new Intl.NumberFormat('en-GB', { style: 'currency', currency }).format(amountMinor / 100);
}

const palette = {
  surface: '#f4f2ee',
  card: '#ffffff',
  ink: '#1c2326',
  muted: '#5f6a70',
  border: '#dfddd5',
  green: '#0f766e',
  greenSoft: '#e0f4f1',
};

const baseShadow = Platform.select({
  ios: {
    shadowColor: '#1c2326',
    shadowOpacity: 0.08,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 8 },
  },
  android: { elevation: 2 },
  default: {},
});

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: palette.surface,
  },
  content: {
    padding: 18,
    paddingTop: Platform.OS === 'web' ? 86 : 18,
    gap: 14,
    maxWidth: 980,
    width: '100%',
    alignSelf: 'center',
  },
  header: {
    gap: 8,
  },
  kicker: {
    color: palette.green,
    fontWeight: '900',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0,
  },
  title: {
    color: palette.ink,
    fontSize: 30,
    fontWeight: '900',
    lineHeight: 36,
  },
  subtle: {
    color: palette.muted,
    fontSize: 14,
    lineHeight: 20,
  },
  summaryBand: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  summaryItem: {
    flexGrow: 1,
    flexBasis: 76,
    backgroundColor: palette.ink,
    borderRadius: 8,
    padding: 12,
    minHeight: 78,
    justifyContent: 'center',
  },
  summaryValue: {
    color: palette.card,
    fontSize: 22,
    fontWeight: '900',
  },
  summaryLabel: {
    color: '#b9c7c3',
    fontSize: 11,
    fontWeight: '800',
    textTransform: 'uppercase',
    marginTop: 4,
  },
  panel: {
    backgroundColor: palette.card,
    borderRadius: 8,
    padding: 16,
    gap: 12,
    borderWidth: 1,
    borderColor: palette.border,
    ...baseShadow,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 12,
  },
  sectionTitleWrap: {
    flex: 1,
    gap: 4,
  },
  panelTitle: {
    color: palette.ink,
    fontWeight: '900',
    fontSize: 18,
  },
  smallButton: {
    backgroundColor: palette.green,
    borderRadius: 8,
    minHeight: 38,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 12,
    flexShrink: 0,
  },
  smallButtonText: {
    color: palette.card,
    fontWeight: '900',
    fontSize: 13,
  },
  actionStrip: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  secondaryButton: {
    backgroundColor: palette.greenSoft,
    borderRadius: 8,
    minHeight: 38,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 12,
  },
  secondaryButtonText: {
    color: palette.green,
    fontWeight: '900',
    fontSize: 13,
  },
  disabled: {
    opacity: 0.6,
  },
  row: {
    borderTopWidth: 1,
    borderTopColor: '#eeeae2',
    paddingTop: 12,
    gap: 5,
  },
  rowTitle: {
    color: palette.ink,
    fontWeight: '900',
    fontSize: 15,
  },
  rowDetail: {
    color: palette.muted,
    lineHeight: 19,
  },
  linkButton: {
    alignSelf: 'flex-start',
    paddingVertical: 5,
  },
  linkButtonText: {
    color: palette.green,
    fontWeight: '900',
  },
  emptyText: {
    color: palette.muted,
    paddingTop: 8,
  },
});
