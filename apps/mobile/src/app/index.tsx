import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
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
  const [businessPhone, setBusinessPhone] = useState('07700 900100');
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

  const templateText = templateDraft || templateQuery.data?.body || '';
  const missedCalls = callsQuery.data ?? [];
  const outboundMessages = useMemo(
    () => (messagesQuery.data ?? []).filter((message) => message.direction === 'outbound'),
    [messagesQuery.data],
  );

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
            <Text style={styles.title}>Turn missed calls into booked jobs.</Text>
            <Text style={styles.subtle}>
              Dedicated Twilio number, trade-aware SMS, and job admin in one mobile workspace.
            </Text>
          </View>

          <View style={styles.segment}>
            <SegmentButton active={mode === 'signup'} label="Signup" onPress={() => setMode('signup')} />
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
            <Input label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />
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

  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.topbar}>
          <View style={styles.flexShrink}>
            <Text style={styles.kicker}>TradeAlert</Text>
            <Text style={styles.title}>{company?.business_name ?? 'Dashboard'}</Text>
          </View>
          <Pressable style={styles.signOutButton} onPress={() => setToken(null)}>
            <Text style={styles.signOutText}>Sign out</Text>
          </Pressable>
        </View>

        <View style={styles.statsGrid}>
          <Metric label="Twilio number" value={company?.twilio_number ?? 'Pending'} />
          <Metric label="Missed calls" value={String(missedCalls.length)} />
          <Metric label="Queued replies" value={String(outboundMessages.length)} />
          <Metric label="Subscription" value={company?.subscription_status ?? 'Unknown'} />
        </View>

        <View style={styles.panel}>
          <View style={styles.panelHeader}>
            <Text style={styles.panelTitle}>Missed-call reply</Text>
            <Text style={styles.subtle}>{company?.trade?.replace('_', ' ')}</Text>
          </View>
          <TextInput
            value={templateText}
            onChangeText={setTemplateDraft}
            multiline
            style={[styles.input, styles.templateInput]}
          />
          <PrimaryButton
            label="Save template"
            loading={saveTemplateMutation.isPending}
            onPress={() => saveTemplateMutation.mutate()}
          />
          {saveTemplateMutation.error && <Text style={styles.error}>{saveTemplateMutation.error.message}</Text>}
        </View>

        <ListPanel
          title="Recent missed calls"
          empty="No missed calls yet"
          rows={missedCalls.map((call) => ({
            id: call.id,
            title: call.caller_number,
            detail: `${call.status} -> ${new Date(call.created_at).toLocaleString()}`,
          }))}
        />

        <ListPanel
          title="SMS queue"
          empty="No SMS replies yet"
          rows={outboundMessages.slice(0, 5).map((message) => ({
            id: message.id,
            title: message.to_number,
            detail: `${message.status}: ${message.body}`,
          }))}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

function Input(props: React.ComponentProps<typeof TextInput> & { label: string }) {
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

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#f6f7f9',
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
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
    color: '#007a61',
    fontWeight: '800',
    fontSize: 14,
    textTransform: 'uppercase',
  },
  title: {
    color: '#17202a',
    fontSize: 30,
    fontWeight: '800',
    lineHeight: 36,
  },
  subtle: {
    color: '#596674',
    fontSize: 14,
    lineHeight: 20,
  },
  segment: {
    flexDirection: 'row',
    backgroundColor: '#e5e9ee',
    padding: 4,
    borderRadius: 8,
  },
  segmentButton: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderRadius: 6,
  },
  segmentButtonActive: {
    backgroundColor: '#ffffff',
  },
  segmentText: {
    color: '#596674',
    fontWeight: '700',
  },
  segmentTextActive: {
    color: '#17202a',
  },
  panel: {
    backgroundColor: '#ffffff',
    borderRadius: 8,
    padding: 16,
    gap: 12,
    borderWidth: 1,
    borderColor: '#e2e6ea',
  },
  panelHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },
  panelTitle: {
    color: '#17202a',
    fontSize: 18,
    fontWeight: '800',
  },
  field: {
    gap: 6,
  },
  label: {
    color: '#42505f',
    fontSize: 13,
    fontWeight: '700',
  },
  input: {
    minHeight: 44,
    borderWidth: 1,
    borderColor: '#cbd3dc',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: '#17202a',
    backgroundColor: '#ffffff',
    fontSize: 16,
  },
  templateInput: {
    minHeight: 144,
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
    borderColor: '#cbd3dc',
    backgroundColor: '#ffffff',
  },
  chipActive: {
    backgroundColor: '#007a61',
    borderColor: '#007a61',
  },
  chipText: {
    color: '#42505f',
    fontWeight: '700',
  },
  chipTextActive: {
    color: '#ffffff',
  },
  primaryButton: {
    backgroundColor: '#007a61',
    minHeight: 46,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 14,
  },
  primaryButtonText: {
    color: '#ffffff',
    fontWeight: '800',
    fontSize: 15,
  },
  disabled: {
    opacity: 0.6,
  },
  error: {
    color: '#b42318',
    fontWeight: '700',
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  metric: {
    flexGrow: 1,
    flexBasis: 150,
    backgroundColor: '#ffffff',
    borderRadius: 8,
    padding: 14,
    borderWidth: 1,
    borderColor: '#e2e6ea',
    minHeight: 86,
    justifyContent: 'center',
  },
  metricValue: {
    color: '#17202a',
    fontSize: 19,
    fontWeight: '800',
  },
  metricLabel: {
    color: '#596674',
    marginTop: 6,
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  listRow: {
    borderTopWidth: 1,
    borderTopColor: '#edf0f3',
    paddingTop: 12,
    gap: 4,
  },
  rowTitle: {
    color: '#17202a',
    fontWeight: '800',
  },
  rowDetail: {
    color: '#596674',
    lineHeight: 19,
  },
  signOutButton: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#cbd3dc',
    backgroundColor: '#ffffff',
  },
  signOutText: {
    color: '#42505f',
    fontWeight: '800',
  },
});
