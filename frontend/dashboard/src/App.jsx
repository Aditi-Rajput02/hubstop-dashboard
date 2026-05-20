import { useState, useEffect, useCallback } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { api } from './api.js';
import './index.css';

import Sidebar      from './components/Sidebar.jsx';
import TopBar       from './components/TopBar.jsx';
import ThrottleBar  from './components/ThrottleBar.jsx';
import KPICards     from './components/KPICards.jsx';
import ContactsTable from './components/ContactsTable.jsx';
import ContactsPage   from './components/ContactsPage.jsx';
import SequencesPage  from './components/SequencesPage.jsx';
import TemplatesPage  from './components/TemplatesPage.jsx';
import AnalyticsPage  from './components/AnalyticsPage.jsx';
import DealsPage      from './components/DealsPage.jsx';
import QuickActions   from './components/QuickActions.jsx';
import EngineStatus   from './components/EngineStatus.jsx';
import LogTerminal    from './components/LogTerminal.jsx';
import ActivityFeed   from './components/ActivityFeed.jsx';
import RecentActivity from './components/RecentActivity.jsx';

const REFRESH_MS = 30_000;

// ── Shared offline / refresh banner ──────────────────────────────────────────
function StatusBar({ engineOnline, lastRefresh, onRefresh }) {
  return (
    <div className="px-gutter pt-gutter space-y-sm">
      {lastRefresh && (
        <div className="flex items-center justify-end gap-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span className="font-label-md text-on-secondary-container text-[11px]">
            Last updated: {lastRefresh} · auto-refreshes every 30s
          </span>
          <button
            onClick={onRefresh}
            className="font-label-md text-on-tertiary-fixed-variant hover:underline text-[11px]"
          >
            Refresh now
          </button>
        </div>
      )}
      {!engineOnline && (
        <div className="bg-error-container border border-error rounded-xl px-lg py-md flex items-center gap-md">
          <span className="material-symbols-outlined text-error">warning</span>
          <div>
            <p className="font-label-md text-on-error-container font-bold">Backend Offline</p>
            <p className="font-body-sm text-on-error-container">
              Start the FastAPI server:{' '}
              <code className="bg-white/20 px-1 rounded">
                venv\Scripts\uvicorn backend.main:app --reload --port 8000
              </code>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Dashboard page ────────────────────────────────────────────────────────────
function DashboardPage({ kpi, throttle, contacts, contactsLoad, stalled, logs, onActionDone, engineOnline, activityFeed, recentItems, activityLoad }) {
  return (
    <div className="p-gutter space-y-gutter">
      <ThrottleBar throttle={throttle} />
      <KPICards kpi={kpi} />

      {/* Recent Activity cards */}
      <section>
        <RecentActivity items={recentItems} loading={activityLoad} />
      </section>

      <section className="grid grid-cols-12 gap-gutter items-start">
        <ContactsTable contacts={contacts} loading={contactsLoad} />
        <div className="col-span-12 lg:col-span-4 space-y-gutter">
          <QuickActions stalledCount={stalled} onActionDone={onActionDone} />
          <EngineStatus throttle={throttle} engineOnline={engineOnline} />
        </div>
      </section>

      {/* Activity Feed */}
      <section>
        <ActivityFeed activities={activityFeed} loading={activityLoad} />
      </section>

      <section className="grid grid-cols-12 gap-gutter">
        <LogTerminal lines={logs} />
      </section>
    </div>
  );
}

// ── Placeholder pages ─────────────────────────────────────────────────────────
function PlaceholderPage({ title, icon }) {
  return (
    <div className="p-gutter flex flex-col items-center justify-center min-h-[60vh] text-center">
      <span className="material-symbols-outlined text-6xl text-on-secondary-container mb-lg">{icon}</span>
      <h2 className="font-headline-md text-on-surface font-bold mb-sm">{title}</h2>
      <p className="font-body-md text-on-secondary-container">This page is coming soon.</p>
    </div>
  );
}

// ── Root App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [engineOnline, setEngineOnline] = useState(false);
  const [dashboard,    setDashboard]    = useState(null);
  const [contacts,     setContacts]     = useState([]);
  const [contactsLoad, setContactsLoad] = useState(true);
  const [logs,         setLogs]         = useState([]);
  const [lastRefresh,  setLastRefresh]  = useState(null);
  const [activityFeed, setActivityFeed] = useState([]);
  const [recentItems,  setRecentItems]  = useState([]);
  const [activityLoad, setActivityLoad] = useState(true);

  const fetchHealth = useCallback(async () => {
    try { await api.health(); setEngineOnline(true); }
    catch { setEngineOnline(false); }
  }, []);

  const fetchDashboard = useCallback(async () => {
    try { const d = await api.dashboard(); setDashboard(d); }
    catch (e) { console.warn('Dashboard fetch failed:', e.message); }
  }, []);

  const fetchContacts = useCallback(async () => {
    setContactsLoad(true);
    try { const d = await api.contacts(); setContacts(d.contacts || []); }
    catch (e) { console.warn('Contacts fetch failed:', e.message); setContacts([]); }
    finally { setContactsLoad(false); }
  }, []);

  const fetchLogs = useCallback(async () => {
    try { const d = await api.logs(60); setLogs(d.lines || []); }
    catch (e) { console.warn('Logs fetch failed:', e.message); }
  }, []);

  const fetchActivity = useCallback(async () => {
    setActivityLoad(true);
    try {
      const d = await api.activity();
      setActivityFeed(d.activity_feed || []);
      setRecentItems(d.recent_items || []);
    } catch (e) {
      console.warn('Activity fetch failed:', e.message);
    } finally {
      setActivityLoad(false);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    await Promise.all([fetchHealth(), fetchDashboard(), fetchContacts(), fetchLogs(), fetchActivity()]);
    setLastRefresh(new Date().toLocaleTimeString());
  }, [fetchHealth, fetchDashboard, fetchContacts, fetchLogs, fetchActivity]);

  useEffect(() => {
    refreshAll();
    const t = setInterval(refreshAll, REFRESH_MS);
    return () => clearInterval(t);
  }, [refreshAll]);

  const kpi     = dashboard?.kpi      ?? {};
  const throttle = dashboard?.throttle ?? {};
  const stalled  = kpi.stalled_leads  ?? 0;

  return (
    <div className="bg-background text-on-surface font-body-md overflow-x-hidden">
      <Sidebar />

      <main className="ml-64 flex flex-col min-h-screen">
        <TopBar engineOnline={engineOnline} />

        <StatusBar
          engineOnline={engineOnline}
          lastRefresh={lastRefresh}
          onRefresh={refreshAll}
        />

        <Routes>
          {/* Default → dashboard */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          <Route
            path="/dashboard"
            element={
              <DashboardPage
                kpi={kpi}
                throttle={throttle}
                contacts={contacts}
                contactsLoad={contactsLoad}
                stalled={stalled}
                logs={logs}
                onActionDone={refreshAll}
                engineOnline={engineOnline}
                activityFeed={activityFeed}
                recentItems={recentItems}
                activityLoad={activityLoad}
              />
            }
          />

          <Route
            path="/contacts"
            element={
              <ContactsPage
                contacts={contacts}
                loading={contactsLoad}
                onRefresh={fetchContacts}
              />
            }
          />

          <Route path="/sequences" element={<SequencesPage />} />
          <Route path="/templates" element={<TemplatesPage />} />
          <Route path="/analytics"  element={<AnalyticsPage contacts={contacts} contactsLoad={contactsLoad} />} />
          <Route path="/deals"      element={<DealsPage />} />
          <Route path="/logs"       element={<PlaceholderPage title="Logs"        icon="list_alt" />} />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>

        <footer className="mt-auto py-lg px-gutter text-center border-t border-outline-variant bg-surface-container-low">
          <p className="font-label-md text-on-secondary-fixed-variant">
            © 2025 Sequence Automator — CRM Dashboard
          </p>
        </footer>
      </main>
    </div>
  );
}
