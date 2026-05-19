import { useState, useMemo } from 'react';
import ContactDetailModal from './ContactDetailModal.jsx';

const PAGE_SIZE = 25;


// HubSpot hs_lead_status values with colors
const LEAD_STATUS_COLORS = {
  'OPEN':          'border-sky-200 bg-sky-50 text-sky-700',
  'New':           'border-gray-200 bg-gray-50 text-gray-600',
  'Contacted':     'border-blue-200 bg-blue-50 text-blue-700',
  'Followed-up-1': 'border-indigo-200 bg-indigo-50 text-indigo-700',
  'Followed-up-2': 'border-violet-200 bg-violet-50 text-violet-700',
  'Followed-up-3': 'border-purple-200 bg-purple-50 text-purple-700',
  'Replied':       'border-emerald-200 bg-emerald-50 text-emerald-700',
  'Stalled':       'border-amber-200 bg-amber-50 text-amber-700',
  'Re-engaged':    'border-teal-200 bg-teal-50 text-teal-700',
  'Cold':          'border-slate-200 bg-slate-50 text-slate-500',
  'Archived':      'border-slate-200 bg-slate-100 text-slate-400',
};

// All possible HubSpot lead status values
const ALL_LEAD_STATUSES = [
  'All',
  'OPEN',
  'New',
  'Contacted',
  'Followed-up-1',
  'Followed-up-2',
  'Followed-up-3',
  'Replied',
  'Stalled',
  'Re-engaged',
  'Cold',
  'Archived',
];

function LeadStatusBadge({ status }) {
  if (!status) return <span className="status-badge border-gray-200 bg-gray-50 text-gray-400">—</span>;
  return (
    <span className={`status-badge ${LEAD_STATUS_COLORS[status] || 'border-gray-200 bg-gray-50 text-gray-600'}`}>
      {status}
    </span>
  );
}

function timeAgo(isoStr) {
  if (!isoStr) return '—';
  const ms = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 1)  return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)  return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function ContactsPage({ contacts, loading, onRefresh }) {
  const [search,           setSearch]        = useState('');
  const [leadStatusFilter, setLeadStatus]    = useState('All');
  const [page,            setPage]           = useState(0);
  const [sortKey,         setSortKey]        = useState('last_modified');
  const [sortAsc,         setSortAsc]        = useState(false);
  const [selected,        setSelected]       = useState(null);

  // Filter + search + sort
  const filtered = useMemo(() => {
    let list = contacts ?? [];
    if (leadStatusFilter !== 'All') {
      list = list.filter(c => (c.lead_status || '').toLowerCase() === leadStatusFilter.toLowerCase());
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(c =>
        (c.name  || '').toLowerCase().includes(q) ||
        (c.email || '').toLowerCase().includes(q) ||
        (c.lead_type || '').toLowerCase().includes(q)
      );
    }
    list = [...list].sort((a, b) => {
      let av = a[sortKey] ?? '';
      let bv = b[sortKey] ?? '';
      if (sortKey === 'sequence_day') { av = Number(av); bv = Number(bv); }
      if (sortKey === 'last_modified') { av = new Date(av || 0); bv = new Date(bv || 0); }
      if (av < bv) return sortAsc ? -1 : 1;
      if (av > bv) return sortAsc ?  1 : -1;
      return 0;
    });
    return list;
  }, [contacts, leadStatusFilter, search, sortKey, sortAsc]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage   = Math.min(page, totalPages - 1);
  const pageSlice  = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  function handleSort(key) {
    if (sortKey === key) setSortAsc(a => !a);
    else { setSortKey(key); setSortAsc(true); }
    setPage(0);
  }

  function handleSearch(e)    { setSearch(e.target.value); setPage(0); }
  function handleLeadStatus(s){ setLeadStatus(s); setPage(0); }

  function SortIcon({ col }) {
    if (sortKey !== col) return <span className="material-symbols-outlined text-sm opacity-30">unfold_more</span>;
    return <span className="material-symbols-outlined text-sm text-primary">{sortAsc ? 'arrow_upward' : 'arrow_downward'}</span>;
  }

  return (
    <div className="p-gutter space-y-gutter">

      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-headline-md text-on-surface font-bold">Contacts</h2>
          <p className="font-body-sm text-on-secondary-container mt-xs">
            {(contacts ?? []).length} total · {filtered.length} shown
          </p>
        </div>
        <button
          onClick={onRefresh}
          className="flex items-center gap-sm px-md py-sm rounded-lg border border-outline-variant hover:bg-surface-container font-label-md text-on-surface transition-colors"
        >
          <span className="material-symbols-outlined text-base">refresh</span>
          Refresh
        </button>
      </div>

      {/* Search + filter bar */}
      <div className="flex flex-wrap gap-md items-center">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-secondary-container text-base">search</span>
          <input
            type="text"
            value={search}
            onChange={handleSearch}
            placeholder="Search name, email, lead type…"
            className="w-full pl-9 pr-4 py-sm rounded-lg border border-outline-variant bg-surface-container-lowest font-body-sm text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
          />
          {search && (
            <button onClick={() => { setSearch(''); setPage(0); }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-on-secondary-container hover:text-on-surface">
              <span className="material-symbols-outlined text-base">close</span>
            </button>
          )}
        </div>

        {/* HubSpot Lead Status dropdown */}
        <div className="flex items-center gap-xs">
          <span className="material-symbols-outlined text-base text-on-secondary-container">label</span>
          <label className="font-label-md text-on-secondary-container whitespace-nowrap">Lead Status:</label>
          <div className="relative">
            <select
              value={leadStatusFilter}
              onChange={e => handleLeadStatus(e.target.value)}
              className="appearance-none pl-3 pr-8 py-xs rounded-lg border border-outline-variant bg-surface-container-lowest font-label-md text-on-surface focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
            >
              {ALL_LEAD_STATUSES.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <span className="material-symbols-outlined absolute right-2 top-1/2 -translate-y-1/2 text-sm text-on-secondary-container pointer-events-none">
              expand_more
            </span>
          </div>
          {leadStatusFilter !== 'All' && (
            <button
              onClick={() => handleLeadStatus('All')}
              className="flex items-center gap-xs px-sm py-xs rounded-full text-xs border border-outline-variant text-on-secondary-container hover:bg-surface-container transition-colors"
              title="Clear lead status filter"
            >
              <span className="material-symbols-outlined text-xs">close</span>
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Active filter summary */}
      {leadStatusFilter !== 'All' && (
        <div className="flex items-center gap-sm flex-wrap">
          <span className="font-label-sm text-on-secondary-container">Filtering by:</span>
          <span className={`flex items-center gap-xs px-sm py-xs rounded-full border font-label-sm ${LEAD_STATUS_COLORS[leadStatusFilter] || 'border-gray-200 bg-gray-50 text-gray-600'}`}>
            Lead Status: {leadStatusFilter}
            <button onClick={() => handleLeadStatus('All')} className="hover:opacity-70">
              <span className="material-symbols-outlined text-xs">close</span>
            </button>
          </span>
          <button
            onClick={() => handleLeadStatus('All')}
            className="font-label-sm text-on-secondary-container hover:text-on-surface underline"
          >
            Clear all
          </button>
        </div>
      )}

      {/* Table */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48 text-on-secondary-container font-body-sm">
            <span className="material-symbols-outlined animate-spin mr-sm">refresh</span>
            Loading contacts…
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead className="bg-surface-container-low text-on-secondary-fixed-variant font-label-md">
                  <tr>
                    <th className="px-lg py-md cursor-pointer select-none" onClick={() => handleSort('name')}>
                      <div className="flex items-center gap-xs">NAME <SortIcon col="name" /></div>
                    </th>
                    <th className="px-lg py-md cursor-pointer select-none" onClick={() => handleSort('lead_type')}>
                      <div className="flex items-center gap-xs">LEAD TYPE <SortIcon col="lead_type" /></div>
                    </th>
                    <th className="px-lg py-md cursor-pointer select-none" onClick={() => handleSort('lead_status')}>
                      <div className="flex items-center gap-xs">LEAD STATUS <SortIcon col="lead_status" /></div>
                    </th>
                    <th className="px-lg py-md cursor-pointer select-none" onClick={() => handleSort('sequence_day')}>
                      <div className="flex items-center gap-xs">DAY <SortIcon col="sequence_day" /></div>
                    </th>
                    <th className="px-lg py-md cursor-pointer select-none" onClick={() => handleSort('last_modified')}>
                      <div className="flex items-center gap-xs">LAST ACTIVITY <SortIcon col="last_modified" /></div>
                    </th>
                    <th className="px-lg py-md">EMAIL</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant">
                  {pageSlice.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-lg py-xl text-center text-on-secondary-container font-body-sm">
                        {search || leadStatusFilter !== 'All'
                          ? 'No contacts match your search / filter.'
                          : 'No contacts found. Add contacts in HubSpot to get started.'}
                      </td>
                    </tr>
                  ) : (
                    pageSlice.map(c => (
                      <tr
                        key={c.id}
                        className="hover:bg-surface-container-low transition-colors cursor-pointer"
                        onClick={() => setSelected(c)}
                      >
                        <td className="px-lg py-md">
                          <div className="font-body-md font-bold text-on-surface">{c.name || '—'}</div>
                          <div className="font-body-sm text-on-secondary-container">{c.email}</div>
                        </td>
                        <td className="px-lg py-md">
                          <span className="font-body-sm text-on-secondary-container capitalize">
                            {(c.lead_type || 'general').replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="px-lg py-md">
                          <LeadStatusBadge status={c.lead_status} />
                        </td>
                        <td className="px-lg py-md">
                          <span className="font-body-sm text-on-surface">
                            {c.sequence_day > 0 ? `Day ${c.sequence_day}` : '—'}
                          </span>
                        </td>
                        <td className="px-lg py-md text-on-secondary-container font-body-sm">
                          {timeAgo(c.last_modified)}
                        </td>
                        <td className="px-lg py-md">
                          <a
                            href={`mailto:${c.email}`}
                            className="font-body-sm text-primary hover:underline"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {c.email}
                          </a>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="px-lg py-md border-t border-outline-variant flex items-center justify-between">
              <span className="font-body-sm text-on-secondary-container">
                {filtered.length === 0
                  ? 'No results'
                  : `Showing ${safePage * PAGE_SIZE + 1}–${Math.min(safePage * PAGE_SIZE + PAGE_SIZE, filtered.length)} of ${filtered.length}`}
              </span>
              <div className="flex items-center gap-sm">
                <button
                  onClick={() => setPage(0)}
                  disabled={safePage === 0}
                  className="p-xs rounded border border-outline-variant hover:bg-surface-container disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  title="First page"
                >
                  <span className="material-symbols-outlined text-base">first_page</span>
                </button>
                <button
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={safePage === 0}
                  className="flex items-center gap-xs px-md py-xs rounded-lg font-label-md text-on-surface border border-outline-variant hover:bg-surface-container-low disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <span className="material-symbols-outlined text-base">chevron_left</span>
                  Prev
                </button>

                {/* Page number pills */}
                <div className="flex gap-xs">
                  {Array.from({ length: totalPages }, (_, i) => i)
                    .filter(i => Math.abs(i - safePage) <= 2)
                    .map(i => (
                      <button
                        key={i}
                        onClick={() => setPage(i)}
                        className={`w-8 h-8 rounded font-label-md text-sm transition-colors ${
                          i === safePage
                            ? 'bg-primary text-on-primary'
                            : 'border border-outline-variant text-on-secondary-container hover:bg-surface-container'
                        }`}
                      >
                        {i + 1}
                      </button>
                    ))}
                </div>

                <button
                  onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                  disabled={safePage >= totalPages - 1}
                  className="flex items-center gap-xs px-md py-xs rounded-lg font-label-md text-on-surface border border-outline-variant hover:bg-surface-container-low disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  Next
                  <span className="material-symbols-outlined text-base">chevron_right</span>
                </button>
                <button
                  onClick={() => setPage(totalPages - 1)}
                  disabled={safePage >= totalPages - 1}
                  className="p-xs rounded border border-outline-variant hover:bg-surface-container disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  title="Last page"
                >
                  <span className="material-symbols-outlined text-base">last_page</span>
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Contact detail modal */}
      {selected && (
        <ContactDetailModal
          contact={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
