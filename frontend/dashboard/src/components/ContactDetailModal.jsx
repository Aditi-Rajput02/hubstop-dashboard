import { useEffect, useState } from 'react';
import { api } from '../api.js';

const STATUS_COLORS = {
  Replied:  'border-emerald-200 bg-emerald-50 text-emerald-700',
  Active:   'border-blue-200 bg-blue-50 text-blue-700',
  Stalled:  'border-amber-200 bg-amber-50 text-amber-700',
  Complete: 'border-purple-200 bg-purple-50 text-purple-700',
  New:      'border-gray-200 bg-gray-50 text-gray-600',
  Cold:     'border-slate-200 bg-slate-50 text-slate-500',
  Archived: 'border-slate-200 bg-slate-100 text-slate-400',
};

function StatusBadge({ status }) {
  return (
    <span className={`status-badge ${STATUS_COLORS[status] || STATUS_COLORS.New}`}>
      {status}
    </span>
  );
}

function InfoRow({ label, value, mono = false }) {
  if (!value && value !== 0) return null;
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-label-md text-on-secondary-container text-[11px] uppercase tracking-wide">{label}</span>
      <span className={`font-body-sm text-on-surface ${mono ? 'font-mono text-xs' : ''}`}>{value}</span>
    </div>
  );
}

function timeAgo(isoStr) {
  if (!isoStr) return null;
  const ms = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 1)  return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)  return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function ContactDetailModal({ contact, onClose }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);

  useEffect(() => {
    if (!contact?.id) return;
    setLoading(true);
    setError(null);
    api.getContact(contact.id)
      .then(d => { setDetail(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [contact?.id]);

  // Close on Escape key
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const c = detail || contact; // fall back to list data while loading

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* Panel */}
      <div className="relative bg-surface-container-lowest border border-outline-variant rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">

        {/* Header */}
        <div className="flex items-start justify-between p-lg border-b border-outline-variant sticky top-0 bg-surface-container-lowest z-10">
          <div className="flex items-center gap-md">
            {/* Avatar */}
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-lg select-none">
              {(c?.name || c?.email || '?')[0].toUpperCase()}
            </div>
            <div>
              <h2 className="font-headline-sm text-on-surface font-bold leading-tight">
                {c?.name || '—'}
              </h2>
              <a
                href={`mailto:${c?.email}`}
                className="font-body-sm text-primary hover:underline"
              >
                {c?.email}
              </a>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-xs rounded-lg hover:bg-surface-container text-on-secondary-container hover:text-on-surface transition-colors"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {/* Body */}
        <div className="p-lg space-y-lg">

          {loading && (
            <div className="flex items-center justify-center py-xl text-on-secondary-container font-body-sm">
              <span className="material-symbols-outlined animate-spin mr-sm">refresh</span>
              Loading contact details…
            </div>
          )}

          {error && (
            <div className="bg-error-container border border-error rounded-xl px-lg py-md text-on-error-container font-body-sm">
              <span className="font-bold">Error: </span>{error}
            </div>
          )}

          {/* Status row */}
          <div className="flex flex-wrap gap-sm items-center">
            <StatusBadge status={c?.status || 'New'} />
            {c?.sequence_day > 0 && (
              <span className="px-md py-xs rounded-full border border-blue-200 bg-blue-50 text-blue-700 font-label-md text-xs">
                Day {c.sequence_day}
              </span>
            )}
            {c?.replied && (
              <span className="px-md py-xs rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700 font-label-md text-xs">
                ✓ Replied
              </span>
            )}
            {c?.sequence_complete && (
              <span className="px-md py-xs rounded-full border border-purple-200 bg-purple-50 text-purple-700 font-label-md text-xs">
                ✓ Sequence Complete
              </span>
            )}
          </div>

          {/* Contact info */}
          <div className="bg-surface-container-low rounded-xl p-md grid grid-cols-2 gap-md">
            <InfoRow label="Lead Type"   value={(c?.lead_type || 'general').replace(/_/g, ' ')} />
            <InfoRow label="Lead Status" value={c?.lead_status || c?.status} />
            <InfoRow label="Expo / Event" value={c?.expo_name} />
            <InfoRow label="Company"     value={c?.company} />
          </div>

          {/* Sequence info */}
          <div>
            <h3 className="font-label-md text-on-secondary-container uppercase tracking-wide text-[11px] mb-sm">
              Sequence Progress
            </h3>
            <div className="bg-surface-container-low rounded-xl p-md grid grid-cols-2 gap-md">
              <InfoRow label="Current Day"    value={c?.sequence_day > 0 ? `Day ${c.sequence_day}` : 'Not started'} />
              <InfoRow label="Replied At"     value={c?.replied_at ? timeAgo(c.replied_at) : null} />
              <InfoRow label="Last Modified"  value={c?.last_modified ? timeAgo(c.last_modified) : null} />
              <InfoRow label="Thread ID"      value={c?.thread_id} mono />
            </div>
          </div>

          {/* HubSpot link */}
          {c?.id && (
            <a
              href={`https://app.hubspot.com/contacts/${c.id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-sm px-lg py-sm rounded-xl border border-outline-variant hover:bg-surface-container font-label-md text-on-surface transition-colors w-full justify-center"
            >
              <span className="material-symbols-outlined text-base">open_in_new</span>
              View in HubSpot CRM
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
