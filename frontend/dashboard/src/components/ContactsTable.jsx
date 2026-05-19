import { useState } from 'react';
import ContactDetailModal from './ContactDetailModal.jsx';

function StatusBadge({ status }) {
  const styles = {
    Replied:  'border-emerald-200 bg-emerald-50 text-emerald-700',
    Active:   'border-blue-200 bg-blue-50 text-blue-700',
    Stalled:  'border-amber-200 bg-amber-50 text-amber-700',
    Complete: 'border-purple-200 bg-purple-50 text-purple-700',
    New:      'border-gray-200 bg-gray-50 text-gray-600',
    Cold:     'border-slate-200 bg-slate-50 text-slate-500',
    Archived: 'border-slate-200 bg-slate-100 text-slate-400',
  };
  return (
    <span className={`status-badge ${styles[status] || styles.New}`}>
      {status}
    </span>
  );
}

function timeAgo(isoStr) {
  if (!isoStr) return '—';
  const ms = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 1)   return 'just now';
  if (mins < 60)  return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)   return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const PAGE_SIZE = 10;

export default function ContactsTable({ contacts, loading }) {
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState(null);

  if (loading) {
    return (
      <div className="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm p-lg">
        <div className="flex items-center justify-center h-32 text-on-secondary-container font-body-sm">
          <span className="material-symbols-outlined animate-spin mr-sm">refresh</span>
          Loading contacts...
        </div>
      </div>
    );
  }

  const total      = contacts?.length ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const safePage   = Math.min(page, totalPages - 1);
  const pageSlice  = (contacts ?? []).slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  return (
    <>
      <div className="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm overflow-hidden">
        <div className="p-lg border-b border-outline-variant flex justify-between items-center">
          <h3 className="font-headline-sm text-headline-sm">Recent Interactions</h3>
          <span className="font-label-md text-on-secondary-container">{total} contacts</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-surface-container-low text-on-secondary-fixed-variant font-label-md">
              <tr>
                <th className="px-lg py-md">NAME</th>
                <th className="px-lg py-md">LEAD TYPE</th>
                <th className="px-lg py-md">STATUS</th>
                <th className="px-lg py-md">DAY</th>
                <th className="px-lg py-md">LAST ACTIVITY</th>
                <th className="px-lg py-md text-right">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant">
              {total === 0 ? (
                <tr>
                  <td colSpan={6} className="px-lg py-xl text-center text-on-secondary-container font-body-sm">
                    No contacts found. Add contacts in HubSpot to get started.
                  </td>
                </tr>
              ) : (
                pageSlice.map(c => (
                  <tr
                    key={c.id}
                    className="hover:bg-surface-container-low transition-colors group cursor-pointer"
                    onClick={() => setSelected(c)}
                  >
                    <td className="px-lg py-md">
                      <div className="font-body-md font-bold text-on-surface">{c.name}</div>
                      <div className="font-body-sm text-on-secondary-container">{c.email}</div>
                    </td>
                    <td className="px-lg py-md">
                      <span className="font-body-sm text-on-secondary-container capitalize">
                        {(c.lead_type || 'general').replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-lg py-md">
                      <StatusBadge status={c.status} />
                    </td>
                    <td className="px-lg py-md">
                      <span className="font-body-sm text-on-surface">
                        {c.sequence_day > 0 ? `Day ${c.sequence_day}` : '—'}
                      </span>
                    </td>
                    <td className="px-lg py-md text-on-secondary-container font-body-sm">
                      {timeAgo(c.last_modified)}
                    </td>
                    <td className="px-lg py-md text-right">
                      <button
                        className="material-symbols-outlined text-outline group-hover:text-primary"
                        onClick={(e) => { e.stopPropagation(); setSelected(c); }}
                        title="View details"
                      >
                        open_in_new
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination controls */}
        {totalPages > 1 && (
          <div className="px-lg py-md border-t border-outline-variant flex items-center justify-between">
            <span className="font-body-sm text-on-secondary-container">
              Showing {safePage * PAGE_SIZE + 1}–{Math.min(safePage * PAGE_SIZE + PAGE_SIZE, total)} of {total}
            </span>
            <div className="flex items-center gap-sm">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={safePage === 0}
                className="flex items-center gap-xs px-md py-xs rounded-lg font-label-md text-on-surface border border-outline-variant hover:bg-surface-container-low disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <span className="material-symbols-outlined text-base">chevron_left</span>
                Prev
              </button>
              <span className="font-label-md text-on-secondary-container px-sm">
                {safePage + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={safePage >= totalPages - 1}
                className="flex items-center gap-xs px-md py-xs rounded-lg font-label-md text-on-surface border border-outline-variant hover:bg-surface-container-low disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                Next
                <span className="material-symbols-outlined text-base">chevron_right</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Contact detail modal */}
      {selected && (
        <ContactDetailModal
          contact={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
}
