import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { ComponentProps } from 'react';
import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';

const trades = ['plumber', 'electrician', 'roofer', 'locksmith', 'gas_engineer', 'builder'];
const callbackWindows = [5, 10, 30, 60];
const appointmentWindows = ['4-hour', 'same day', 'next day', '1 week'];

export default function DashboardScreen() {
  const { bootstrapped, token, setToken } = useAuth();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<'signup' | 'login'>('signup');
  const [email, setEmail] = useState('ian@example.com');
  const [password, setPassword] = useState('password123');
  const [businessName, setBusinessName] = useState("Ian's Plumbing");
  const [businessPhone, setBusinessPhone] = useState('07432870739');
  const [trade, setTrade] = useState('plumber');
  const [callbackWindow, setCallbackWindow] = useState(10);
  const [appointmentWindow, setAppointmentWindow] = useState('4-hour');
  const [templateDraft, setTemplateDraft] = useState('');

  const meQuery = useQuery({
    queryKey: ['me', token],
    queryFn: () => api.me(token ?? ''),
    enabled: Boolean(token),
  });
  const companyQuery = useQuery({
    queryKey: ['company', token],
    queryFn: () => api.company(token ?? ''),
    enabled: Boolean(token),
  });
  const templateQuery = useQuery({
    queryKey: ['template', token],
    queryFn: () => api.template(token ?? ''),
    enabled: Boolean(token),
  });
  const callsQuery = useQuery({
    queryKey: ['calls', token],
    queryFn: () => api.calls(token ?? ''),
    enabled: Boolean(token),
  });
  const messagesQuery = useQuery({
    queryKey: ['messages', token],
    queryFn: () => api.messages(token ?? ''),
    enabled: Boolean(token),
  });
  const jobsQuery = useQuery({
    queryKey: ['jobs', token],
    queryFn: () => api.jobs(token ?? ''),
    enabled: Boolean(token),
  });
  const stockQuery = useQuery({
    queryKey: ['stock', token],
    queryFn: () => api.stock(token ?? ''),
    enabled: Boolean(token),
  });

  const authMutation = useMutation({
    mutationFn: async () => {
      if (mode === 'login') {
        return api.login({ email, password });
      }
      return api.register({
        email,
        password,
        business_name: businessName,
        trade,
        callback_window_minutes: callbackWindow,
        appointment_window: appointmentWindow,
        business_phone: businessPhone,
      });
    },
    onSuccess: async (result) => {
      await setToken(result.access_token);
      queryClient.setQueryData(['me', result.access_token], result.user);
    },
  });

  const saveTemplateMutation = useMutation({
    mutationFn: () => api.updateTemplate(token ?? '', templateDraft || templateQuery.data?.body || ''),
    onSuccess: (template) => {
      queryClient.setQueryData(['template', token], template);
      setTemplateDraft(template.body);
    },
  });

  const missedCalls = callsQuery.data ?? [];
  const outboundMessages = useMemo(
    () => (messagesQuery.data ?? []).filter((message) => message.direction === 'outbound'),
    [messagesQuery.data],
  );
  const sentMessages = useMemo(
    () => outboundMessages.filter((message) => message.status === 'sent'),
    [outboundMessages],
  );
  const templateText = templateDraft || templateQuery.data?.body || '';

  if (!bootstrapped) {
    return (
      <SafeAreaView style={styles.centered}>
        <ActivityIndicator />
      </SafeAreaView>
    );
  }

  if (!token) {
    return (
      <SafeAreaView style={styles.screen}>
        <ScrollView contentContainerStyle={styles.content}>
          <View style={styles.header}>
            <Text style={styles.kicker}>TradeAlert</Text>
            <Text style={styles.title}>Your phone catches the missed calls.</Text>
            <Text style={styles.subtle}>
              Android agent on the trade phone, VPS dashboard for the trail, no Twilio or dongles.
            </Text>
          </View>

          <View style={styles.segment}>
            <SegmentButton active={mode === 'signup'} label="Create" onPress={() => setMode('signup')} />
            <SegmentButton active={mode === 'login'} label="Login" onPress={() => setMode('login')} />
          </View>

          <View style={styles.panel}>
            {mode === 'signup' && (
              <>
                <Input label="Business" value={businessName} onChangeText={setBusinessName} />
                <Input label="Phone" value={businessPhone} onChangeText={setBusinessPhone} keyboardType="phone-pad" />
                <Text style={styles.label}>Trade</Text>
                <ChipRow values={trades} selected={trade} onSelect={setTrade} />
                <Text style={styles.label}>Callback window</Text>
                <ChipRow
                  values={callbackWindows.map(String)}
                  selected={String(callbackWindow)}
                  onSelect={(value) => setCallbackWindow(Number(value))}
                />
                <Text style={styles.label}>Appointment window</Text>
                <ChipRow values={appointmentWindows} selected={appointmentWindow} onSelect={setAppointmentWindow} />
              </>
            )}
            <Input
              label="Email"
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
            />
            <Input label="Password" value={password} onChangeText={setPassword} secureTextEntry />
            <PrimaryButton
              label={mode === 'signup' ? 'Create company' : 'Sign in'}
              loading={authMutation.isPending}
              onPress={() => authMutation.mutate()}
            />
            {authMutation.error && <Text style={styles.error}>{authMutation.error.message}</Text>}
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  const company = companyQuery.data ?? meQuery.data?.company;
  const agentStatus = sentMessages.length > 0 || missedCalls.length > 0 ? 'Live on Android' : 'Ready to test';

  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.topbar}>
          <View style={styles.flexShrink}>
            <Text style={styles.kicker}>TradeAlert</Text>
            <Text style={styles.title}>{company?.business_name ?? 'Today'}</Text>
            <Text style={styles.subtle}>
              {company?.business_phone ?? 'Business phone'} is the line your customers already know.
            </Text>
          </View>
          <Pressable style={styles.signOutButton} onPress={() => setToken(null)}>
            <Text style={styles.signOutText}>Sign out</Text>
          </Pressable>
        </View>

        <View style={styles.agentPanel}>
          <View style={styles.statusRow}>
            <Text style={styles.agentPanelTitle}>Phone agent</Text>
            <StatusPill label={agentStatus} tone="good" />
          </View>
          <Text style={styles.agentText}>
            Missed calls are detected on the Android phone. SMS replies are sent from the phone SIM.
          </Text>
          <View style={styles.statsGrid}>
            <Metric label="Missed calls" value={String(missedCalls.length)} />
            <Metric label="SMS sent" value={String(sentMessages.length)} />
            <Metric label="Open jobs" value={String(jobsQuery.data?.length ?? 0)} />
            <Metric label="Van items" value={String(stockQuery.data?.length ?? 0)} />
          </View>
        </View>

        <View style={styles.panel}>
          <View style={styles.panelHeader}>
            <View>
              <Text style={styles.panelTitle}>Missed-call reply</Text>
              <Text style={styles.subtle}>{company?.trade?.replace('_', ' ') ?? 'trade'} template</Text>
            </View>
            <StatusPill label={`${company?.callback_window_minutes ?? 10} min`} tone="neutral" />
          </View>
          <TextInput
            value={templateText}
            onChangeText={setTemplateDraft}
            multiline
            style={[styles.input, styles.templateInput]}
          />
          <PrimaryButton
            label="Save reply wording"
            loading={saveTemplateMutation.isPending}
            onPress={() => saveTemplateMutation.mutate()}
          />
          {saveTemplateMutation.error && <Text style={styles.error}>{saveTemplateMutation.error.message}</Text>}
        </View>

        <View style={styles.workflowGrid}>
          <FeatureTile title="Jobs" detail="Create jobs from missed calls, add address, photos, and notes." />
          <FeatureTile title="Invoices" detail="Attach job photos, send SumUp links, prepare insurance reports." />
          <FeatureTile title="Van stock" detail="Track fittings in the van and prep a Screwfix basket." />
          <FeatureTile title="Maps" detail="Tap customer addresses to open Google Maps." />
        </View>

        <ListPanel
          title="Recent missed calls"
          empty="No missed calls yet"
          rows={missedCalls.slice(0, 4).map((call) => ({
            id: call.id,
            title: call.caller_number,
            detail: `${call.status} - ${new Date(call.created_at).toLocaleString()}`,
          }))}
        />

        <ListPanel
          title="Recent SMS replies"
          empty="No SMS replies yet"
          rows={outboundMessages.slice(0, 4).map((message) => ({
            id: message.id,
            title: message.to_number,
            detail: `${message.status}: ${message.body}`,
          }))}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

function Input(props: ComponentProps<typeof TextInput> & { label: string }) {
  const { label, ...inputProps } = props;
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput {...inputProps} style={styles.input} placeholderTextColor="#7c8794" />
    </View>
  );
}

function SegmentButton({ active, label, onPress }: { active: boolean; label: string; onPress: () => void }) {
  return (
    <Pressable style={[styles.segmentButton, active && styles.segmentButtonActive]} onPress={onPress}>
      <Text style={[styles.segmentText, active && styles.segmentTextActive]}>{label}</Text>
    </Pressable>
  );
}

function ChipRow({ values, selected, onSelect }: { values: string[]; selected: string; onSelect: (value: string) => void }) {
  return (
    <View style={styles.chipRow}>
      {values.map((value) => (
        <Pressable
          key={value}
          style={[styles.chip, selected === value && styles.chipActive]}
          onPress={() => onSelect(value)}>
          <Text style={[styles.chipText, selected === value && styles.chipTextActive]}>{value.replace('_', ' ')}</Text>
        </Pressable>
      ))}
    </View>
  );
}

function PrimaryButton({ label, loading, onPress }: { label: string; loading?: boolean; onPress: () => void }) {
  return (
    <Pressable style={[styles.primaryButton, loading && styles.disabled]} onPress={onPress} disabled={loading}>
      <Text style={styles.primaryButtonText}>{loading ? 'Working...' : label}</Text>
    </Pressable>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricValue} numberOfLines={1}>
        {value}
      </Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

function FeatureTile({ title, detail }: { title: string; detail: string }) {
  return (
    <View style={styles.featureTile}>
      <Text style={styles.featureTitle}>{title}</Text>
      <Text style={styles.featureDetail}>{detail}</Text>
    </View>
  );
}

function StatusPill({ label, tone }: { label: string; tone: 'good' | 'neutral' }) {
  return (
    <View style={[styles.pill, tone === 'good' ? styles.goodPill : styles.neutralPill]}>
      <Text style={[styles.pillText, tone === 'good' ? styles.goodPillText : styles.neutralPillText]}>{label}</Text>
    </View>
  );
}

function ListPanel({
  title,
  empty,
  rows,
}: {
  title: string;
  empty: string;
  rows: { id: string; title: string; detail: string }[];
}) {
  return (
    <View style={styles.panel}>
      <Text style={styles.panelTitle}>{title}</Text>
      {rows.length === 0 ? (
        <Text style={styles.subtle}>{empty}</Text>
      ) : (
        rows.map((row) => (
          <View key={row.id} style={styles.listRow}>
            <Text style={styles.rowTitle}>{row.title}</Text>
            <Text style={styles.rowDetail} numberOfLines={3}>
              {row.detail}
            </Text>
          </View>
        ))
      )}
    </View>
  );
}

const palette = {
  surface: '#f4f2ee',
  card: '#ffffff',
  ink: '#1c2326',
  muted: '#5f6a70',
  border: '#dfddd5',
  green: '#0f766e',
  greenSoft: '#e0f4f1',
  amberSoft: '#fff4dc',
  amber: '#986314',
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
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
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
    paddingTop: 16,
  },
  topbar: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 12,
  },
  flexShrink: {
    flexShrink: 1,
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
  segment: {
    flexDirection: 'row',
    backgroundColor: '#e7e4dc',
    padding: 4,
    borderRadius: 10,
  },
  segmentButton: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderRadius: 8,
  },
  segmentButtonActive: {
    backgroundColor: palette.card,
  },
  segmentText: {
    color: palette.muted,
    fontWeight: '800',
  },
  segmentTextActive: {
    color: palette.ink,
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
  agentPanel: {
    backgroundColor: palette.ink,
    borderRadius: 8,
    padding: 16,
    gap: 14,
    ...baseShadow,
  },
  agentText: {
    color: '#dce5e2',
    fontSize: 14,
    lineHeight: 20,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  panelHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },
  panelTitle: {
    color: palette.ink,
    fontSize: 18,
    fontWeight: '900',
  },
  agentPanelTitle: {
    color: palette.card,
    fontSize: 18,
    fontWeight: '900',
  },
  field: {
    gap: 6,
  },
  label: {
    color: '#42505f',
    fontSize: 13,
    fontWeight: '800',
  },
  input: {
    minHeight: 44,
    borderWidth: 1,
    borderColor: '#cbc8bf',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: palette.ink,
    backgroundColor: palette.card,
    fontSize: 16,
  },
  templateInput: {
    minHeight: 134,
    textAlignVertical: 'top',
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#cbc8bf',
    backgroundColor: palette.card,
  },
  chipActive: {
    backgroundColor: palette.green,
    borderColor: palette.green,
  },
  chipText: {
    color: '#42505f',
    fontWeight: '800',
  },
  chipTextActive: {
    color: palette.card,
  },
  primaryButton: {
    backgroundColor: palette.green,
    minHeight: 46,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 14,
  },
  primaryButtonText: {
    color: palette.card,
    fontWeight: '900',
    fontSize: 15,
  },
  disabled: {
    opacity: 0.6,
  },
  error: {
    color: '#b42318',
    fontWeight: '800',
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  metric: {
    flexGrow: 1,
    flexBasis: 130,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 8,
    padding: 12,
    minHeight: 74,
    justifyContent: 'center',
  },
  metricValue: {
    color: palette.card,
    fontSize: 22,
    fontWeight: '900',
  },
  metricLabel: {
    color: '#b9c7c3',
    marginTop: 6,
    fontSize: 11,
    fontWeight: '800',
    textTransform: 'uppercase',
  },
  workflowGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  featureTile: {
    flexGrow: 1,
    flexBasis: 155,
    backgroundColor: palette.card,
    borderRadius: 8,
    padding: 14,
    borderWidth: 1,
    borderColor: palette.border,
    minHeight: 118,
    ...baseShadow,
  },
  featureTitle: {
    color: palette.ink,
    fontWeight: '900',
    fontSize: 16,
  },
  featureDetail: {
    color: palette.muted,
    marginTop: 8,
    lineHeight: 19,
  },
  listRow: {
    borderTopWidth: 1,
    borderTopColor: '#eeeae2',
    paddingTop: 12,
    gap: 4,
  },
  rowTitle: {
    color: palette.ink,
    fontWeight: '900',
  },
  rowDetail: {
    color: palette.muted,
    lineHeight: 19,
  },
  signOutButton: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#cbc8bf',
    backgroundColor: palette.card,
  },
  signOutText: {
    color: '#42505f',
    fontWeight: '900',
  },
  pill: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  goodPill: {
    backgroundColor: palette.greenSoft,
  },
  neutralPill: {
    backgroundColor: palette.amberSoft,
  },
  pillText: {
    fontSize: 12,
    fontWeight: '900',
  },
  goodPillText: {
    color: palette.green,
  },
  neutralPillText: {
    color: palette.amber,
  },
});
