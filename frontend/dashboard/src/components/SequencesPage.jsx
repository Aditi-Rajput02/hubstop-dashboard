import { useState, useEffect, useCallback } from 'react';
import { api } from '../api.js';

const PAGE_SIZE = 5;
const LEAD_TYPES = [
  { value: 'bulk_liquid',   label: 'Bulk Liquid'   },
  { value: 'private_label', label: 'Private Label' },
  { value: 'general',       label: 'General'       },
];
const EXPO_SOURCES = [
  'Singapore Expo',
  'Delhi Trade Fair',
  'Mumbai Build Expo',
  'Bangalore Expo',
  'Website',
  'Referral',
];

// ── Create Sequence Modal ─────────────────────────────────────────────────────
function CreateSequenceModal({ contacts, onClose, onCreated }) {
  const today = new Date().toISOString().split('T')[0];
  const [expoSource, setExpoSource] = useState(EXPO_SOURCES[0]);
  const [customName, setCustomName] = useState('');
  const [leadType,   setLeadType]   = useState('general');
  const [date,       setDate]       = useState(today);
  const [selected,   setSelected]   = useState(new Set());
  const [search,     setSearch]     = useState('');
  const [saving,     setSaving]     = useState(false);
  const [error,      setError]      = useState('');

  // The actual expo_name sent to HubSpot: use custom if provided, else the dropdown value
  const resolvedName = customName.trim() || expoSource;

  const filtered = contacts.filter(c => {
    const q = search.toLowerCase();
    return !q || c.name.toLowerCase().includes(q) || c.email.toLowerCase().includes(q);
  });

  function toggleContact(id) {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (selected.size === filtered.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(filtered.map(c => c.id)));
    }
  }

  async function handleCreate() {
    if (!resolvedName) { setError('Please select an expo source.'); return; }
    if (selected.size === 0) { setError('Select at least one contact.'); return; }
    setSaving(true); setError('');
    try {
      const res = await api.createSequence(resolvedName, leadType, date, [...selected], expoSource);
      onCreated(res);
    } catch (e) {
      setError(e.message || 'Failed to create sequence.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-md">
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-lg py-md border-b border-outline-variant">
          <h3 className="font-bold text-on-surface" style={{fontSize:'18px'}}>Create New Sequence</h3>
          <button onClick={onClose} className="text-on-secondary-container hover:text-on-surface">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-lg space-y-md">
          {/* Expo Source dropdown */}
          <div>
            <label className="font-label-md text-on-secondary-container block mb-xs">Expo Source *</label>
            <select value={expoSource} onChange={e => { setExpoSource(e.target.value); setCustomName(''); }}
              className="w-full px-md py-sm border border-outline-variant rounded-lg bg-surface-container-lowest font-body-md text-on-surface focus:outline-none focus:ring-1 focus:ring-primary">
              {EXPO_SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <p className="font-body-sm text-on-secondary-container mt-xs">
              Sets <code className="bg-surface-container px-xs rounded">expo_source</code> + <code className="bg-surface-container px-xs rounded">expo_name</code> in HubSpot.
            </p>
          </div>

          {/* Optional custom name override */}
          <div>
            <label className="font-label-md text-on-secondary-container block mb-xs">Custom Sequence Name <span className="text-[10px]">(optional — overrides expo source label)</span></label>
            <input type="text" value={customName} onChange={e => setCustomName(e.target.value)}
              placeholder={`Leave blank to use "${expoSource}"`}
              className="w-full px-md py-sm border border-outline-variant rounded-lg bg-surface-container-lowest font-body-md text-on-surface focus:outline-none focus:ring-1 focus:ring-primary" />
            {resolvedName && (
              <p className="font-body-sm text-emerald-700 mt-xs">
                ✓ Will be saved as: <strong>{resolvedName}</strong>
              </p>
            )}
          </div>

          {/* Lead type + date */}
          <div className="grid grid-cols-2 gap-md">
            <div>
              <label className="font-label-md text-on-secondary-container block mb-xs">Lead Type *</label>
              <select value={leadType} onChange={e => setLeadType(e.target.value)}
                className="w-full px-md py-sm border border-outline-variant rounded-lg bg-surface-container-lowest font-body-md text-on-surface focus:outline-none focus:ring-1 focus:ring-primary">
                {LEAD_TYPES.map(lt => <option key={lt.value} value={lt.value}>{lt.label}</option>)}
              </select>
            </div>
            <div>
              <label className="font-label-md text-on-secondary-container block mb-xs">Day 1 Start Date *</label>
              <input type="date" value={date} onChange={e => setDate(e.target.value)}
                className="w-full px-md py-sm border border-outline-variant rounded-lg bg-surface-container-lowest font-body-md text-on-surface focus:outline-none focus:ring-1 focus:ring-primary" />
              <p className="font-body-sm text-on-secondary-container mt-xs">First email fires on this date.</p>
            </div>
          </div>

          {/* Contact picker */}
          <div>
            <div className="flex items-center justify-between mb-xs">
              <label className="font-label-md text-on-secondary-container">Select Contacts * ({selected.size} selected)</label>
              <button onClick={toggleAll} className="font-label-md text-on-tertiary-fixed-variant hover:underline text-[11px]">
                {selected.size === filtered.length ? 'Deselect all' : 'Select all'}
              </button>
            </div>
            <input type="text" value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search by name or email…"
              className="w-full px-md py-sm border border-outline-variant rounded-lg bg-surface-container-lowest font-body-sm text-on-surface focus:outline-none focus:ring-1 focus:ring-primary mb-sm" />
            <div className="border border-outline-variant rounded-lg overflow-hidden max-h-48 overflow-y-auto divide-y divide-outline-variant">
              {filtered.length === 0 ? (
                <p className="px-md py-sm font-body-sm text-on-secondary-container">No contacts found.</p>
              ) : filtered.map(c => (
                <label key={c.id} className="flex items-center gap-md px-md py-sm hover:bg-surface-container cursor-pointer">
                  <input type="checkbox" checked={selected.has(c.id)} onChange={() => toggleContact(c.id)}
                    className="rounded border-outline-variant" />
                  <div className="flex-1 min-w-0">
                    <div className="font-body-sm text-on-surface truncate">{c.name}</div>
                    <div className="font-body-sm text-on-secondary-container truncate text-[11px]">{c.email}</div>
                  </div>
                  <span className="font-label-md text-[10px] text-on-secondary-container">{c.status}</span>
                </label>
              ))}
            </div>
          </div>

          {error && <p className="font-body-sm text-error">{error}</p>}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-md px-lg py-md border-t border-outline-variant">
          <button onClick={onClose} className="px-md py-sm border border-outline-variant rounded-lg font-label-md text-on-secondary-container hover:bg-surface-container transition-colors">
            Cancel
          </button>
          <button onClick={handleCreate} disabled={saving}
            className="flex items-center gap-sm px-lg py-sm bg-primary text-on-primary rounded-lg font-label-md hover:opacity-90 disabled:opacity-50 transition-all">
            <span className="material-symbols-outlined text-base">add</span>
            {saving ? 'Creating…' : `Create Sequence (${selected.size} contacts)`}
          </button>
        </div>
      </div>
    </div>
  );
}

function Toggle({ enabled, onChange }) {
  return (
    <button
      onClick={onChange}
      className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${enabled ? 'bg-emerald-500' : 'bg-outline-variant'}`}
    >
      <span className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${enabled ? 'translate-x-5' : 'translate-x-0'}`} />
    </button>
  );
}

function StatusBadge({ status }) {
  const cls = status === 'Active'
    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
    : 'bg-amber-50 text-amber-700 border-amber-200';
  return (
    <span className={`inline-flex items-center px-sm py-xs rounded-full border font-label-md ${cls}`}>
      {status}
    </span>
  );
}

export default function SequencesPage() {
  const [sequences,   setSequences]   = useState([]);
  const [allContacts, setAllContacts] = useState([]);
  const [stats,       setStats]       = useState({});
  const [loading,     setLoading]     = useState(true);
  const [offline,     setOffline]     = useState(false);
  const [filter,      setFilter]      = useState('All');
  const [page,        setPage]        = useState(0);
  const [showCreate,  setShowCreate]  = useState(false);
  const [createMsg,   setCreateMsg]   = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await api.sequences();
      // Map backend fields → component fields
      const mapped = (d.sequences || []).map(s => ({
        id:        s.id,
        name:      s.name,
        sub:       s.sub,
        status:    s.status,
        contacts:  s.contacts,
        replyRate: s.reply_rate,
        active:    s.active,
        replied:   s.replied,
        complete:  s.complete,
        stalled:   s.stalled,
        newLeads:  s.new,
        maxDay:    s.max_day,
        enabled:   s.status === 'Active',
      }));
      setSequences(mapped);
      setStats(d.stats || {});
      setOffline(false);
    } catch (e) {
      console.warn('Sequences fetch failed:', e.message);
      setOffline(true);
    } finally {
      setLoading(false);
    }
  }, []);

  // Also load contacts for the modal picker
  const loadContacts = useCallback(async () => {
    try {
      const d = await api.contacts();
      setAllContacts(d.contacts || []);
    } catch (e) {
      console.warn('Contacts fetch failed:', e.message);
    }
  }, []);

  useEffect(() => { load(); loadContacts(); }, [load, loadContacts]);

  const filtered = sequences.filter(s =>
    filter === 'All' ? true : s.status === filter
  );
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage   = Math.min(page, totalPages - 1);
  const pageSlice  = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  function toggleEnabled(id) {
    setSequences(prev => prev.map(s =>
      s.id === id ? { ...s, enabled: !s.enabled, status: !s.enabled ? 'Active' : 'Paused' } : s
    ));
  }

  const totalActive   = stats.active_sequences ?? sequences.filter(s => s.status === 'Active').length;
  const totalContacts = stats.total_contacts   ?? sequences.reduce((a, s) => a + s.contacts, 0);
  const avgReply      = stats.avg_reply_rate   ?? (sequences.length ? (sequences.reduce((a,s)=>a+s.replyRate,0)/sequences.length).toFixed(1) : 0);

  return (
    <div className="p-gutter space-y-gutter">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-lg">
        <div>
          <h2 className="font-headline-lg text-on-surface mb-xs" style={{fontSize:'32px',fontWeight:700}}>Sequences</h2>
          <p className="font-body-md text-on-secondary-container">Manage your automated outreach workflows and track performance metrics.</p>
        </div>
        <div className="flex items-center gap-md">
          <div className="flex bg-surface-container-high rounded-lg p-xs">
            {['All','Active','Paused'].map(f => (
              <button key={f} onClick={() => { setFilter(f); setPage(0); }}
                className={`px-md py-xs rounded font-label-md transition-colors ${filter === f ? 'bg-white shadow text-on-surface' : 'text-on-secondary-container hover:text-on-surface'}`}>
                {f}
              </button>
            ))}
          </div>
          <button
            onClick={() => { setCreateMsg(''); setShowCreate(true); }}
            className="flex items-center gap-sm px-lg py-sm bg-primary text-on-primary rounded-lg font-label-md hover:opacity-90 transition-all"
          >
            <span className="material-symbols-outlined text-base">add</span>
            New Sequence
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-lg">
        {[
          { label: 'Total Active',    value: totalActive,                    sub: '↑ 8%',    subCls: 'text-emerald-600' },
          { label: 'Total Contacts',  value: totalContacts.toLocaleString(), sub: 'Last 30d', subCls: 'text-on-secondary-container' },
          { label: 'Avg. Reply Rate', value: `${avgReply}%`,                 sub: '↑ 2.1%',  subCls: 'text-emerald-600' },
          { label: 'Completion',      value: '92%',                          sub: 'Efficiency',subCls:'text-on-secondary-container' },
        ].map(card => (
          <div key={card.label} className="bg-surface-container-lowest border border-outline-variant p-lg rounded-xl">
            <p className="font-label-md text-on-secondary-container mb-xs">{card.label}</p>
            <div className="flex items-baseline gap-sm">
              <span className="text-on-surface font-bold" style={{fontSize:'28px'}}>{card.value}</span>
              <span className={`font-label-md ${card.subCls}`}>{card.sub}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Success banner after creating a sequence */}
      {createMsg && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl px-lg py-md flex items-center justify-between gap-md">
          <div className="flex items-center gap-md">
            <span className="material-symbols-outlined text-emerald-600">check_circle</span>
            <p className="font-body-sm text-emerald-800">{createMsg}</p>
          </div>
          <button onClick={() => setCreateMsg('')} className="text-emerald-600 hover:text-emerald-800">
            <span className="material-symbols-outlined text-base">close</span>
          </button>
        </div>
      )}

      {/* Offline / loading banners */}
      {offline && (
        <div className="bg-error-container border border-error rounded-xl px-lg py-md flex items-center gap-md">
          <span className="material-symbols-outlined text-error">wifi_off</span>
          <p className="font-body-sm text-on-error-container">Backend offline — start the FastAPI server to see real HubSpot sequences.</p>
        </div>
      )}

      {/* Table */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
        {/* Table header row with refresh */}
        <div className="px-lg py-sm bg-surface-container-low border-b border-outline-variant flex items-center justify-between">
          <span className="font-label-md text-on-secondary-container">
            {loading ? 'Loading from HubSpot…' : `${sequences.length} sequence${sequences.length !== 1 ? 's' : ''} from HubSpot`}
          </span>
          <button onClick={load} className="flex items-center gap-xs font-label-md text-on-secondary-container hover:text-on-surface transition-colors">
            <span className="material-symbols-outlined text-base">refresh</span>
            Refresh
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low border-b border-outline-variant">
                {['Expo / Campaign','Lead Type','Status','Contacts','Replied','Active','Reply Rate','Enable','Actions'].map((h,i) => (
                  <th key={h} className={`px-lg py-md font-label-md text-on-secondary-container uppercase tracking-wider ${i===8?'text-right':''}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant">
              {loading ? (
                <tr><td colSpan={9} className="px-lg py-xl text-center text-on-secondary-container font-body-sm">
                  <span className="material-symbols-outlined animate-spin mr-sm align-middle">refresh</span>Loading sequences from HubSpot…
                </td></tr>
              ) : pageSlice.length === 0 ? (
                <tr><td colSpan={9} className="px-lg py-xl text-center text-on-secondary-container font-body-sm">
                  {offline ? 'Backend offline — no data available.' : 'No sequences found.'}
                </td></tr>
              ) : pageSlice.map(s => (
                <tr key={s.id} className="hover:bg-surface-container-low transition-colors group">
                  <td className="px-lg py-md">
                    <div className="font-headline-sm text-on-surface">{s.name}</div>
                    <div className="font-body-sm text-on-secondary-container">Day {s.maxDay > 0 ? s.maxDay : '—'} reached</div>
                  </td>
                  <td className="px-lg py-md">
                    <span className="font-body-sm text-on-surface capitalize">{s.sub}</span>
                  </td>
                  <td className="px-lg py-md"><StatusBadge status={s.status} /></td>
                  <td className="px-lg py-md font-body-md text-on-surface">{s.contacts.toLocaleString()}</td>
                  <td className="px-lg py-md font-body-md text-on-surface">{s.replied}</td>
                  <td className="px-lg py-md font-body-md text-on-surface">{s.active}</td>
                  <td className="px-lg py-md">
                    <div className="flex items-center gap-sm">
                      <span className="font-body-md text-on-surface">{s.replyRate}%</span>
                      <div className="w-16 h-1.5 bg-surface-container-high rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${s.replyRate > 20 ? 'bg-emerald-500' : 'bg-amber-400'}`} style={{width:`${Math.min(s.replyRate,100)}%`}} />
                      </div>
                    </div>
                  </td>
                  <td className="px-lg py-md"><Toggle enabled={s.enabled} onChange={() => toggleEnabled(s.id)} /></td>
                  <td className="px-lg py-md text-right">
                    <button className="p-xs text-on-secondary-container hover:text-primary transition-colors"><span className="material-symbols-outlined">edit</span></button>
                    <button className="p-xs text-on-secondary-container hover:text-primary transition-colors"><span className="material-symbols-outlined">more_vert</span></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {/* Pagination */}
        <div className="px-lg py-md bg-surface-container-low flex items-center justify-between border-t border-outline-variant">
          <span className="font-body-sm text-on-secondary-container">
            Showing {filtered.length === 0 ? 0 : safePage * PAGE_SIZE + 1}–{Math.min(safePage * PAGE_SIZE + PAGE_SIZE, filtered.length)} of {filtered.length} sequences
          </span>
          <div className="flex gap-sm">
            <button onClick={() => setPage(p => Math.max(0, p-1))} disabled={safePage===0}
              className="px-md py-xs border border-outline-variant rounded bg-surface-container-lowest font-label-md text-on-secondary-container hover:bg-surface-container disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
              Previous
            </button>
            <button onClick={() => setPage(p => Math.min(totalPages-1, p+1))} disabled={safePage>=totalPages-1}
              className="px-md py-xs border border-outline-variant rounded bg-surface-container-lowest font-label-md text-on-surface hover:bg-surface-container disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Create Sequence Modal */}
      {showCreate && (
        <CreateSequenceModal
          contacts={allContacts}
          onClose={() => setShowCreate(false)}
          onCreated={(res) => {
            setShowCreate(false);
            setCreateMsg(
              `✓ Sequence "${res.sequence_name}" created — ${res.updated} contact${res.updated !== 1 ? 's' : ''} updated in HubSpot. Day 1 starts on ${res.followup_date}.`
            );
            load(); // refresh the sequences list
          }}
        />
      )}

      {/* Bento bottom */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-lg">
        <div className="md:col-span-2 bg-[#0F172A] text-white p-xl rounded-xl relative overflow-hidden flex flex-col justify-between min-h-[220px]">
          <div className="relative z-10">
            <h3 className="font-headline-md mb-sm" style={{fontSize:'20px',fontWeight:600}}>Ready for Global Scale?</h3>
            <p className="text-slate-300 font-body-md max-w-lg">Unlock AI-driven sequence optimization and predictive reply analytics with our Enterprise plan.</p>
          </div>
          <div className="relative z-10 mt-lg">
            <button className="bg-white text-[#0F172A] px-lg py-md rounded-lg font-label-md hover:bg-slate-100 transition-colors">Upgrade Now</button>
          </div>
          <div className="absolute -right-12 -bottom-12 w-64 h-64 bg-slate-800 rounded-full opacity-50 blur-3xl" />
        </div>
        <div className="bg-surface-container-lowest border border-outline-variant p-lg rounded-xl flex flex-col items-center justify-center text-center">
          <div className="w-16 h-16 bg-surface-container-high rounded-full flex items-center justify-center mb-md">
            <span className="material-symbols-outlined text-primary" style={{fontSize:'32px'}}>auto_awesome</span>
          </div>
          <h4 className="font-headline-sm mb-xs">Optimization Tip</h4>
          <p className="font-body-sm text-on-secondary-container px-md">Sequences with more than 3 follow-up steps see a 45% higher reply rate on average.</p>
        </div>
      </div>
    </div>
  );
}
