import { useState, useMemo, useCallback } from 'react';
import ContactDetailModal from './ContactDetailModal.jsx';

// ── CSV Export ────────────────────────────────────────────────────────────────
function exportContactsToCSV(contacts, filename = 'crm-export.csv') {
  if (!contacts || contacts.length === 0) return;
  const headers = ['Name', 'Email', 'Phone', 'Expo Source', 'Lead Status', 'Last Modified'];
  const rows = contacts.map(c => [
    c.name || '',
    c.email || '',
    c.phone || '',
    c.expo_name || '',
    c.lead_status || '',
    c.last_modified || '',
  ].map(v => `"${String(v).replace(/"/g, '""')}"`).join(','));
  const csv = [headers.join(','), ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const EXPO_SOURCES = ['Singapore', 'Delhi', 'Mumbai', 'Bangalore', 'Website', 'Referral'];

const EXPO_COLORS = {
  Singapore: { bar: '#4f46e5', light: '#eef2ff', text: '#3730a3' },
  Delhi:     { bar: '#0891b2', light: '#ecfeff', text: '#0e7490' },
  Mumbai:    { bar: '#059669', light: '#ecfdf5', text: '#047857' },
  Bangalore: { bar: '#d97706', light: '#fffbeb', text: '#b45309' },
  Website:   { bar: '#7c3aed', light: '#f5f3ff', text: '#6d28d9' },
  Referral:  { bar: '#db2777', light: '#fdf2f8', text: '#be185d' },
  Other:     { bar: '#64748b', light: '#f8fafc', text: '#475569' },
};

function getThisQuarterRange() {
  const now = new Date();
  const q = Math.floor(now.getMonth() / 3);
  const start = new Date(now.getFullYear(), q * 3, 1);
  const end   = new Date(now.getFullYear(), q * 3 + 3, 0, 23, 59, 59, 999);
  return { start, end };
}

function quarterLabel() {
  const now = new Date();
  const q = Math.floor(now.getMonth() / 3) + 1;
  return `Q${q} ${now.getFullYear()}`;
}

function isThisQuarter(isoStr) {
  if (!isoStr) return false;
  const d = new Date(isoStr);
  const { start, end } = getThisQuarterRange();
  return d >= start && d <= end;
}

function normaliseExpoSource(contact) {
  // Try expo_name first, then lead_type as fallback label
  const raw = (contact.expo_name || '').trim();
  if (!raw) return 'Other';
  // Case-insensitive match against known sources
  const match = EXPO_SOURCES.find(s => raw.toLowerCase().includes(s.toLowerCase()));
  return match || raw || 'Other';
}

// ── Expo Source Report ────────────────────────────────────────────────────────
// Contact list drawer shown when a bar is clicked
function ExpoContactsDrawer({ source, contacts, onClose, onSelectContact }) {
  const colors = EXPO_COLORS[source] || EXPO_COLORS.Other;
  return (
    <div className="fixed inset-0 z-40 flex justify-end" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-50 w-full max-w-md bg-surface-container-lowest border-l border-outline-variant shadow-2xl flex flex-col h-full">
        <div className="flex items-center justify-between p-lg border-b border-outline-variant" style={{ backgroundColor: colors.light }}>
          <div>
            <h3 className="font-headline-sm font-bold" style={{ color: colors.text }}>{source}</h3>
            <p className="font-body-sm text-on-secondary-container">{contacts.length} lead{contacts.length !== 1 ? 's' : ''} this quarter</p>
          </div>
          <button onClick={onClose} className="p-xs rounded-lg hover:bg-black/10 transition-colors">
            <span className="material-symbols-outlined text-on-secondary-container">close</span>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto divide-y divide-outline-variant">
          {contacts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-xl text-on-secondary-container font-body-sm">
              <span className="material-symbols-outlined text-4xl mb-sm opacity-40">person_off</span>
              No contacts from {source} this quarter.
            </div>
          ) : (
            contacts.map(c => (
              <button
                key={c.id}
                onClick={() => onSelectContact(c)}
                className="w-full text-left px-lg py-md hover:bg-surface-container-low transition-colors flex items-center gap-md"
              >
                <div className="w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0"
                  style={{ backgroundColor: colors.light, color: colors.text }}>
                  {(c.name || c.email || '?')[0].toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-body-md font-bold text-on-surface truncate">{c.name || '—'}</div>
                  <div className="font-body-sm text-on-secondary-container truncate">{c.email}</div>
                </div>
                <div className="flex-shrink-0">
                  <span className="font-label-md text-xs px-sm py-xs rounded-full border"
                    style={{ backgroundColor: colors.light, color: colors.text, borderColor: colors.bar + '40' }}>
                    {c.lead_status || c.status || 'New'}
                  </span>
                </div>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function LeadsByExpoSource({ contacts, loading }) {
  const [selectedSource, setSelectedSource] = useState(null);
  const [selectedContact, setSelectedContact] = useState(null);
  const [chartType, setChartType] = useState('bar'); // 'bar' | 'pie'

  // Filter to this quarter only
  const quarterContacts = useMemo(() => {
    return (contacts || []).filter(c => isThisQuarter(c.last_modified));
  }, [contacts]);

  // Count per expo source
  const sourceCounts = useMemo(() => {
    const counts = {};
    EXPO_SOURCES.forEach(s => { counts[s] = []; });
    quarterContacts.forEach(c => {
      const src = normaliseExpoSource(c);
      if (!counts[src]) counts[src] = [];
      counts[src].push(c);
    });
    // Build sorted array (known sources first, then others)
    const rows = EXPO_SOURCES.map(s => ({ source: s, contacts: counts[s] || [], count: (counts[s] || []).length }));
    // Add any unknown sources
    Object.keys(counts).forEach(k => {
      if (!EXPO_SOURCES.includes(k) && counts[k].length > 0) {
        rows.push({ source: k, contacts: counts[k], count: counts[k].length });
      }
    });
    return rows;
  }, [quarterContacts]);

  const maxCount = Math.max(...sourceCounts.map(r => r.count), 1);
  const total = quarterContacts.length;

  // Pie chart segments
  const pieSegments = useMemo(() => {
    let offset = 0;
    const circumference = 2 * Math.PI * 15.9;
    return sourceCounts.filter(r => r.count > 0).map(r => {
      const pct = total > 0 ? r.count / total : 0;
      const dash = pct * circumference;
      const seg = { ...r, dash, offset, pct };
      offset += dash;
      return seg;
    });
  }, [sourceCounts, total]);

  const drawerContacts = selectedSource
    ? (sourceCounts.find(r => r.source === selectedSource)?.contacts || [])
    : [];

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
      {/* Header */}
      <div className="p-lg border-b border-outline-variant">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-md">
          <div>
            <div className="flex items-center gap-sm mb-xs">
              <span className="material-symbols-outlined text-primary" style={{fontSize:'20px'}}>bar_chart</span>
              <h3 className="font-headline-sm text-on-surface font-bold">Leads by Expo Source</h3>
              <span className="px-sm py-xs rounded-full bg-primary/10 text-primary font-label-md text-xs font-bold">
                {quarterLabel()} · This Quarter
              </span>
            </div>
            <p className="font-body-sm text-on-secondary-container">
              {loading ? 'Loading…' : `${total} contact${total !== 1 ? 's' : ''} added this quarter across all sources. Click a bar to see contacts.`}
            </p>
          </div>
          {/* Chart type toggle */}
          <div className="flex items-center gap-xs bg-surface-container p-xs rounded-lg border border-outline-variant self-start">
            {[['bar','Bar Chart','bar_chart'],['pie','Pie Chart','pie_chart']].map(([v,l,icon]) => (
              <button key={v} onClick={() => setChartType(v)}
                className={`flex items-center gap-xs px-md py-xs font-label-md rounded-md transition-colors ${chartType===v ? 'bg-primary text-on-primary' : 'text-on-secondary-container hover:bg-surface-container-low'}`}>
                <span className="material-symbols-outlined" style={{fontSize:'16px'}}>{icon}</span>
                {l}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chart area */}
      <div className="p-lg">
        {loading ? (
          <div className="flex items-center justify-center h-48 text-on-secondary-container font-body-sm">
            <span className="material-symbols-outlined animate-spin mr-sm">refresh</span>
            Loading CRM data…
          </div>
        ) : chartType === 'bar' ? (
          /* ── Bar Chart ── */
          <div className="space-y-sm">
            {sourceCounts.map(({ source, count }) => {
              const colors = EXPO_COLORS[source] || EXPO_COLORS.Other;
              const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
              const isActive = selectedSource === source;
              return (
                <button
                  key={source}
                  onClick={() => setSelectedSource(count > 0 ? source : null)}
                  className={`w-full text-left group rounded-lg p-sm transition-all ${count > 0 ? 'cursor-pointer hover:bg-surface-container-low' : 'cursor-default opacity-60'} ${isActive ? 'ring-2 ring-primary/40 bg-surface-container-low' : ''}`}
                >
                  <div className="flex items-center gap-md mb-xs">
                    <span className="font-label-md text-on-surface w-24 flex-shrink-0">{source}</span>
                    <div className="flex-1 h-8 bg-surface-container rounded-md overflow-hidden relative">
                      <div
                        className="h-full rounded-md transition-all duration-500 flex items-center justify-end pr-sm"
                        style={{ width: `${Math.max(pct, count > 0 ? 4 : 0)}%`, backgroundColor: colors.bar }}
                      >
                        {pct > 20 && (
                          <span className="font-label-md text-white font-bold text-xs">{count}</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-sm flex-shrink-0">
                      <span className="font-bold text-on-surface w-8 text-right">{count}</span>
                      {count > 0 && (
                        <span className="material-symbols-outlined text-on-secondary-container group-hover:text-primary transition-colors" style={{fontSize:'18px'}}>
                          {isActive ? 'expand_less' : 'chevron_right'}
                        </span>
                      )}
                    </div>
                  </div>
                  {total > 0 && (
                    <div className="flex items-center gap-md pl-[7rem]">
                      <span className="font-body-sm text-on-secondary-container">
                        {count > 0 ? `${((count / total) * 100).toFixed(1)}% of quarter total` : 'No leads this quarter'}
                      </span>
                    </div>
                  )}
                </button>
              );
            })}
            {total === 0 && (
              <div className="text-center py-xl text-on-secondary-container font-body-sm">
                <span className="material-symbols-outlined text-4xl block mb-sm opacity-40">event_busy</span>
                No contacts added this quarter yet.
              </div>
            )}
          </div>
        ) : (
          /* ── Pie Chart ── */
          <div className="flex flex-col lg:flex-row items-center gap-xl">
            <div className="relative w-56 h-56 flex-shrink-0">
              {total === 0 ? (
                <svg className="w-full h-full" viewBox="0 0 36 36">
                  <circle cx="18" cy="18" r="15.9" fill="transparent" stroke="#e2e8f0" strokeWidth="4" />
                </svg>
              ) : (
                <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                  {pieSegments.map((seg, i) => (
                    <circle
                      key={seg.source}
                      cx="18" cy="18" r="15.9"
                      fill="transparent"
                      stroke={(EXPO_COLORS[seg.source] || EXPO_COLORS.Other).bar}
                      strokeWidth="4"
                      strokeDasharray={`${seg.dash} ${2 * Math.PI * 15.9}`}
                      strokeDashoffset={-seg.offset}
                      strokeLinecap="butt"
                      className="cursor-pointer transition-all hover:opacity-80"
                      onClick={() => setSelectedSource(seg.source)}
                      style={{ filter: selectedSource === seg.source ? 'brightness(1.15)' : 'none' }}
                    />
                  ))}
                </svg>
              )}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="font-bold text-on-surface" style={{fontSize:'28px'}}>{total}</span>
                <span className="font-label-md text-on-secondary-container text-xs">Total Leads</span>
              </div>
            </div>
            <div className="flex-1 space-y-sm w-full">
              {sourceCounts.map(({ source, count }) => {
                const colors = EXPO_COLORS[source] || EXPO_COLORS.Other;
                const isActive = selectedSource === source;
                return (
                  <button
                    key={source}
                    onClick={() => setSelectedSource(count > 0 ? source : null)}
                    className={`w-full flex items-center justify-between gap-md p-sm rounded-lg transition-all ${count > 0 ? 'cursor-pointer hover:bg-surface-container-low' : 'cursor-default opacity-50'} ${isActive ? 'ring-2 ring-primary/40 bg-surface-container-low' : ''}`}
                  >
                    <div className="flex items-center gap-sm">
                      <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: colors.bar }} />
                      <span className="font-label-md text-on-surface">{source}</span>
                    </div>
                    <div className="flex items-center gap-sm">
                      <span className="font-bold text-on-surface">{count}</span>
                      <span className="font-body-sm text-on-secondary-container w-12 text-right">
                        {total > 0 ? `${((count / total) * 100).toFixed(1)}%` : '0%'}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Drawer */}
      {selectedSource && (
        <ExpoContactsDrawer
          source={selectedSource}
          contacts={drawerContacts}
          onClose={() => setSelectedSource(null)}
          onSelectContact={(c) => { setSelectedContact(c); setSelectedSource(null); }}
        />
      )}

      {/* Contact detail modal */}
      {selectedContact && (
        <ContactDetailModal
          contact={selectedContact}
          onClose={() => setSelectedContact(null)}
        />
      )}
    </div>
  );
}

// ── Report 2: Follow-up Sequence Completion Rate ──────────────────────────────
const FUNNEL_STAGES = [
  { key: 'New',           label: 'New',           color: '#64748b' },
  { key: 'Contacted',     label: 'Contacted',     color: '#3b82f6' },
  { key: 'Followed-up-1', label: 'Followed-up 1', color: '#6366f1' },
  { key: 'Followed-up-2', label: 'Followed-up 2', color: '#8b5cf6' },
  { key: 'Followed-up-3', label: 'Followed-up 3', color: '#a855f7' },
  { key: 'Replied',       label: 'Replied',       color: '#10b981' },
  { key: 'Cold',          label: 'Cold',          color: '#94a3b8' },
];

const STAGE_COLORS = {
  'New':           '#64748b',
  'Contacted':     '#3b82f6',
  'Followed-up-1': '#6366f1',
  'Followed-up-2': '#8b5cf6',
  'Followed-up-3': '#a855f7',
  'Replied':       '#10b981',
  'Cold':          '#94a3b8',
};

function SequenceFunnelReport({ contacts, loading }) {
  const [view, setView] = useState('funnel'); // 'funnel' | 'table'

  // Count contacts at each lead_status stage
  const stageCounts = contacts.reduce((acc, c) => {
    const s = c.lead_status || 'New';
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {});

  const total = contacts.length;

  // Funnel rows in order
  const funnelRows = FUNNEL_STAGES.map(stage => {
    const count = stageCounts[stage.key] || 0;
    const pctOfTotal = total > 0 ? ((count / total) * 100).toFixed(1) : '0.0';
    return { ...stage, count, pctOfTotal };
  });

  // New → Replied drop-off
  const newCount     = stageCounts['New'] || 0;
  const repliedCount = stageCounts['Replied'] || 0;
  const dropOffPct   = total > 0 ? ((repliedCount / total) * 100).toFixed(1) : '0.0';

  // Per-expo breakdown
  const expoMap = {};
  contacts.forEach(c => {
    const expo = normaliseExpoSource(c);
    if (!expoMap[expo]) expoMap[expo] = { total: 0, replied: 0 };
    expoMap[expo].total += 1;
    if ((c.lead_status || '').toLowerCase() === 'replied') expoMap[expo].replied += 1;
  });
  const expoRows = Object.entries(expoMap)
    .map(([expo, d]) => ({
      expo,
      total: d.total,
      replied: d.replied,
      replyRate: d.total > 0 ? ((d.replied / d.total) * 100).toFixed(1) : '0.0',
    }))
    .sort((a, b) => parseFloat(b.replyRate) - parseFloat(a.replyRate));

  const maxCount = Math.max(...funnelRows.map(r => r.count), 1);

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
      {/* Header */}
      <div className="p-lg border-b border-outline-variant">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-md">
          <div>
            <div className="flex items-center gap-sm mb-xs">
              <span className="material-symbols-outlined text-primary" style={{fontSize:'20px'}}>funnel</span>
              <h3 className="font-headline-sm text-on-surface font-bold">Follow-up Sequence Completion Rate</h3>
            </div>
            <p className="font-body-sm text-on-secondary-container">
              {loading ? 'Loading…' : `${total} total contacts · ${repliedCount} replied (${dropOffPct}% reply rate)`}
            </p>
          </div>
          <div className="flex items-center gap-xs bg-surface-container p-xs rounded-lg border border-outline-variant self-start">
            {[['funnel','Funnel','filter_alt'],['table','Per Expo','table_chart']].map(([v,l,icon]) => (
              <button key={v} onClick={() => setView(v)}
                className={`flex items-center gap-xs px-md py-xs font-label-md rounded-md transition-colors ${view===v ? 'bg-primary text-on-primary' : 'text-on-secondary-container hover:bg-surface-container-low'}`}>
                <span className="material-symbols-outlined" style={{fontSize:'16px'}}>{icon}</span>
                {l}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="p-lg">
        {loading ? (
          <div className="flex items-center justify-center h-48 text-on-secondary-container font-body-sm">
            <span className="material-symbols-outlined animate-spin mr-sm">refresh</span>
            Loading CRM data…
          </div>
        ) : view === 'funnel' ? (
          /* ── Funnel View ── */
          <div className="space-y-xs">
            {/* Summary pills */}
            <div className="flex flex-wrap gap-sm mb-lg">
              <div className="flex items-center gap-xs px-md py-xs rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 font-label-md text-xs">
                <span className="material-symbols-outlined" style={{fontSize:'14px'}}>check_circle</span>
                {repliedCount} Replied · {dropOffPct}% reply rate
              </div>
              <div className="flex items-center gap-xs px-md py-xs rounded-full bg-slate-50 border border-slate-200 text-slate-600 font-label-md text-xs">
                <span className="material-symbols-outlined" style={{fontSize:'14px'}}>people</span>
                {total} Total contacts
              </div>
            </div>

            {funnelRows.map((row, i) => {
              const barPct = maxCount > 0 ? (row.count / maxCount) * 100 : 0;
              const prevCount = i > 0 ? funnelRows[i - 1].count : null;
              const dropOff = prevCount !== null && prevCount > 0
                ? `-${(((prevCount - row.count) / prevCount) * 100).toFixed(0)}%`
                : null;
              return (
                <div key={row.key}>
                  {dropOff && row.count < (prevCount || 0) && (
                    <div className="flex items-center gap-xs pl-28 py-xs text-on-secondary-container font-body-sm text-xs opacity-60">
                      <span className="material-symbols-outlined" style={{fontSize:'12px'}}>arrow_downward</span>
                      {dropOff} drop-off
                    </div>
                  )}
                  <div className="flex items-center gap-md">
                    <span className="font-label-md text-on-surface w-28 flex-shrink-0 text-right pr-sm">{row.label}</span>
                    <div className="flex-1 h-9 bg-surface-container rounded-md overflow-hidden">
                      <div
                        className="h-full rounded-md flex items-center px-sm transition-all duration-500"
                        style={{ width: `${Math.max(barPct, row.count > 0 ? 3 : 0)}%`, backgroundColor: row.color }}
                      >
                        {barPct > 15 && (
                          <span className="font-label-md text-white font-bold text-xs">{row.count}</span>
                        )}
                      </div>
                    </div>
                    <div className="w-20 flex-shrink-0 text-right">
                      <span className="font-bold text-on-surface">{row.count}</span>
                      <span className="font-body-sm text-on-secondary-container ml-xs">({row.pctOfTotal}%)</span>
                    </div>
                  </div>
                </div>
              );
            })}

            {total === 0 && (
              <div className="text-center py-xl text-on-secondary-container font-body-sm">
                <span className="material-symbols-outlined text-4xl block mb-sm opacity-40">group_off</span>
                No contacts found in CRM.
              </div>
            )}
          </div>
        ) : (
          /* ── Per Expo Table ── */
          <div>
            <p className="font-body-sm text-on-secondary-container mb-md">Reply rate per expo source — sorted best to worst.</p>
            {expoRows.length === 0 ? (
              <div className="text-center py-xl text-on-secondary-container font-body-sm">
                <span className="material-symbols-outlined text-4xl block mb-sm opacity-40">table_chart</span>
                No data available.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-outline-variant">
                <table className="w-full text-left">
                  <thead className="bg-surface-container-low font-label-md text-on-secondary-container text-xs uppercase tracking-wide">
                    <tr>
                      <th className="px-lg py-md">Expo Source</th>
                      <th className="px-lg py-md text-right">Total</th>
                      <th className="px-lg py-md text-right">Replied</th>
                      <th className="px-lg py-md text-right">Reply Rate</th>
                      <th className="px-lg py-md">Progress</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant">
                    {expoRows.map((row, i) => {
                      const colors = EXPO_COLORS[row.expo] || EXPO_COLORS.Other;
                      const rate = parseFloat(row.replyRate);
                      return (
                        <tr key={row.expo} className="hover:bg-surface-container-low transition-colors">
                          <td className="px-lg py-md">
                            <div className="flex items-center gap-sm">
                              {i === 0 && <span className="material-symbols-outlined text-amber-500" style={{fontSize:'16px'}}>emoji_events</span>}
                              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: colors.bar }} />
                              <span className="font-body-md font-bold text-on-surface">{row.expo}</span>
                            </div>
                          </td>
                          <td className="px-lg py-md text-right font-body-md text-on-surface">{row.total}</td>
                          <td className="px-lg py-md text-right font-body-md text-emerald-700 font-bold">{row.replied}</td>
                          <td className="px-lg py-md text-right">
                            <span className={`font-bold font-label-md px-sm py-xs rounded-full text-xs ${rate >= 20 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : rate >= 10 ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'bg-slate-50 text-slate-600 border border-slate-200'}`}>
                              {row.replyRate}%
                            </span>
                          </td>
                          <td className="px-lg py-md">
                            <div className="w-32 h-2 bg-surface-container rounded-full overflow-hidden">
                              <div className="h-full rounded-full transition-all duration-500"
                                style={{ width: `${Math.min(rate, 100)}%`, backgroundColor: colors.bar }} />
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function AnalyticsPage({ contacts = [], contactsLoad = false }) {
  const now = new Date();
  const lastUpdated = now.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });

  // ── Derived stats ──
  const coldCount = contacts.filter(c => (c.lead_status || '').toLowerCase() === 'cold').length;

  // Stalled: replied but last_modified > 7 days ago
  const stalledContacts = contacts.filter(c => {
    const isReplied = (c.lead_status || '').toLowerCase() === 'replied';
    if (!isReplied) return false;
    const mod = c.last_modified ? new Date(c.last_modified) : null;
    if (!mod) return false;
    const daysSince = (now - mod) / (1000 * 60 * 60 * 24);
    return daysSince > 7;
  });

  // Top performing expo by replied count
  const expoReplyMap = {};
  contacts.forEach(c => {
    const expo = normaliseExpoSource(c);
    if (!expoReplyMap[expo]) expoReplyMap[expo] = { total: 0, replied: 0 };
    expoReplyMap[expo].total += 1;
    if ((c.lead_status || '').toLowerCase() === 'replied') expoReplyMap[expo].replied += 1;
  });
  const topExpo = Object.entries(expoReplyMap)
    .filter(([, d]) => d.replied > 0)
    .sort((a, b) => b[1].replied - a[1].replied)[0];
  const topExpoName = topExpo ? topExpo[0] : null;
  const topExpoReplied = topExpo ? topExpo[1].replied : 0;
  const topExpoRate = topExpo && topExpo[1].total > 0
    ? ((topExpo[1].replied / topExpo[1].total) * 100).toFixed(1)
    : '0.0';

  return (
    <div className="p-gutter space-y-gutter">
      {/* ── Page Header ── */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-md">
        <div>
          <h1 className="font-bold text-on-surface mb-xs" style={{fontSize:'32px'}}>Analytics Dashboard</h1>
          <div className="flex items-center gap-sm">
            <span className="material-symbols-outlined text-on-secondary-container" style={{fontSize:'16px'}}>schedule</span>
            <p className="font-body-sm text-on-secondary-container">
              Last updated: <span className="font-bold text-on-surface">{lastUpdated}</span>
              {contactsLoad && <span className="ml-sm text-primary animate-pulse">· Refreshing…</span>}
            </p>
          </div>
        </div>
        {/* Export CSV */}
        <button
          onClick={() => exportContactsToCSV(contacts, `crm-contacts-${now.toISOString().slice(0,10)}.csv`)}
          disabled={contacts.length === 0}
          className="flex items-center gap-sm px-lg py-sm bg-primary text-on-primary font-label-md rounded-lg hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <span className="material-symbols-outlined" style={{fontSize:'18px'}}>download</span>
          Export to CSV
        </button>
      </div>

      {/* ── Summary Callout Cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-md">
        {/* Total contacts */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-lg flex items-start gap-md">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-primary" style={{fontSize:'20px'}}>group</span>
          </div>
          <div>
            <div className="font-bold text-on-surface" style={{fontSize:'28px'}}>{contacts.length}</div>
            <div className="font-label-md text-on-secondary-container">Total Contacts</div>
          </div>
        </div>

        {/* Cold leads */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-lg flex items-start gap-md">
          <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-slate-500" style={{fontSize:'20px'}}>ac_unit</span>
          </div>
          <div>
            <div className="font-bold text-on-surface" style={{fontSize:'28px'}}>{coldCount}</div>
            <div className="font-label-md text-on-secondary-container">Cold Leads</div>
            <div className="font-body-sm text-slate-400 text-xs mt-xs">Need re-engagement</div>
          </div>
        </div>

        {/* Stalled conversations */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-lg flex items-start gap-md">
          <div className="w-10 h-10 rounded-lg bg-amber-50 flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-amber-500" style={{fontSize:'20px'}}>hourglass_empty</span>
          </div>
          <div>
            <div className="font-bold text-on-surface" style={{fontSize:'28px'}}>{stalledContacts.length}</div>
            <div className="font-label-md text-on-secondary-container">Stalled Conversations</div>
            <div className="font-body-sm text-amber-500 text-xs mt-xs">Replied · silent 7+ days</div>
          </div>
        </div>

        {/* Top performing expo */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-lg flex items-start gap-md">
          <div className="w-10 h-10 rounded-lg bg-amber-50 flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-amber-500" style={{fontSize:'20px'}}>emoji_events</span>
          </div>
          <div className="min-w-0">
            <div className="font-bold text-on-surface truncate" style={{fontSize:'20px'}}>
              {topExpoName || '—'}
            </div>
            <div className="font-label-md text-on-secondary-container">Top Expo Source</div>
            {topExpoName && (
              <div className="font-body-sm text-emerald-600 text-xs mt-xs">
                {topExpoReplied} replies · {topExpoRate}% rate
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Weekly Email Summary Banner ── */}
      <div className="bg-primary/5 border border-primary/20 rounded-lg p-lg flex flex-col sm:flex-row items-start sm:items-center justify-between gap-md">
        <div className="flex items-start gap-md">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 mt-xs">
            <span className="material-symbols-outlined text-primary" style={{fontSize:'20px'}}>mail</span>
          </div>
          <div>
            <div className="font-label-md font-bold text-on-surface mb-xs">Weekly CRM Summary Email</div>
            <p className="font-body-sm text-on-secondary-container">
              A summary of this dashboard — new leads, reply rates, cold count, and top expo — is sent every Monday morning per Phase 6 plan.
            </p>
          </div>
        </div>
        <a
          href="mailto:?subject=HubStop%20Weekly%20CRM%20Summary&body=View%20the%20live%20dashboard%20at%20your%20dashboard%20URL."
          className="flex items-center gap-sm px-lg py-sm border border-primary text-primary font-label-md rounded-lg hover:bg-primary/10 transition-colors flex-shrink-0 whitespace-nowrap"
        >
          <span className="material-symbols-outlined" style={{fontSize:'16px'}}>send</span>
          Share Dashboard Link
        </a>
      </div>
       {/* ── Report 1: Follow-up Sequence Completion Rate ── */}
      <SequenceFunnelReport contacts={contacts} loading={contactsLoad} />
      {/* ── Report 2: Leads by Expo Source ── */}
      <LeadsByExpoSource contacts={contacts} loading={contactsLoad} />
      
    </div>
  );
}
