import { useState, useRef, useEffect } from 'react';

// ── Helpers ───────────────────────────────────────────────────────────────────

function getInitials(name) {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function formatTime(isoStr) {
  if (!isoStr) return '—';
  const d = new Date(isoStr);
  const now = new Date();
  const diffMs = now - d;
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffDays === 0) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  if (diffDays === 1) return 'Yesterday';
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

// ── Avatar ────────────────────────────────────────────────────────────────────

function Avatar({ name }) {
  const initials = getInitials(name);
  const hasName = name && name !== 'Unknown';

  if (!hasName) {
    return (
      <div className="w-8 h-8 rounded-full bg-gray-100 border border-gray-200 flex items-center justify-center flex-shrink-0">
        <span className="material-symbols-outlined text-gray-400 text-[18px]">person</span>
      </div>
    );
  }

  return (
    <div className="w-8 h-8 rounded-full bg-[#e8f4f8] border border-[#b8dde8] flex items-center justify-center flex-shrink-0">
      <span className="text-[11px] font-bold text-[#0e7490] leading-none">{initials}</span>
    </div>
  );
}

// ── Type badge ────────────────────────────────────────────────────────────────

function TypeBadge({ type }) {
  const map = {
    Sent:     'border border-gray-300 text-gray-700 bg-white',
    Reply:    'border border-emerald-300 text-emerald-700 bg-emerald-50',
    Stalled:  'border border-amber-300 text-amber-700 bg-amber-50',
    Complete: 'border border-purple-300 text-purple-700 bg-purple-50',
    New:      'border border-blue-300 text-blue-700 bg-blue-50',
  };
  return (
    <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded ${map[type] || map.Sent}`}>
      {type}
    </span>
  );
}

// ── Single feed row ───────────────────────────────────────────────────────────

function FeedRow({ item, expanded, onToggle }) {
  const verb = item.type === 'Reply' ? 'replied to' : 'was sent';
  const hasName = item.contact_name && item.contact_name !== 'Unknown';

  return (
    <div className="border-b border-gray-100 last:border-b-0">
      <div
        className="flex items-center gap-3 px-5 py-3.5 hover:bg-gray-50 transition-colors cursor-pointer"
        onClick={onToggle}
      >
        {/* Expand chevron */}
        <span
          className={`material-symbols-outlined text-gray-400 text-[16px] flex-shrink-0 transition-transform duration-150 ${expanded ? 'rotate-90' : ''}`}
        >
          chevron_right
        </span>

        {/* Avatar */}
        <Avatar name={item.contact_name} />

        {/* Description */}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-800 truncate">
            {hasName && (
              <span className="font-semibold text-[#0e7490] mr-1 hover:underline cursor-pointer">
                {item.contact_name}
              </span>
            )}
            <span className="text-gray-500">{verb} </span>
            <span className="font-semibold text-gray-800">{item.subject || '(no subject)'}</span>
          </p>
          {item.email && (
            <p className="text-[11px] text-gray-400 truncate mt-0.5">{item.email}</p>
          )}
        </div>

        {/* Badge + time */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <TypeBadge type={item.type} />
          <span className="text-[11px] text-gray-400 w-16 text-right tabular-nums">
            {formatTime(item.timestamp)}
          </span>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-14 pb-4 pt-2 bg-gray-50 border-t border-gray-100">
          <div className="grid grid-cols-2 gap-x-8 gap-y-1.5 text-[12px]">
            {item.email && (
              <div>
                <span className="text-gray-400">Email: </span>
                <span className="text-gray-700">{item.email}</span>
              </div>
            )}
            {item.lead_type && (
              <div>
                <span className="text-gray-400">Lead type: </span>
                <span className="text-gray-700 capitalize">{item.lead_type.replace(/_/g, ' ')}</span>
              </div>
            )}
            {item.sequence_day > 0 && (
              <div>
                <span className="text-gray-400">Sequence day: </span>
                <span className="text-gray-700">Day {item.sequence_day}</span>
              </div>
            )}
            {item.expo_name && (
              <div>
                <span className="text-gray-400">Expo: </span>
                <span className="text-gray-700">{item.expo_name}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Filter dropdown ───────────────────────────────────────────────────────────

const FILTERS = ['All activity types', 'Sent', 'Reply', 'Stalled', 'Complete'];

function FilterDropdown({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  // Close on outside click
  useEffect(() => {
    function handler(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1 text-[13px] font-semibold text-[#0e7490] hover:text-[#0c6478] transition-colors"
      >
        {value}
        <span className="material-symbols-outlined text-[16px]">
          {open ? 'arrow_drop_up' : 'arrow_drop_down'}
        </span>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 min-w-[180px] py-1">
          {FILTERS.map(f => (
            <button
              key={f}
              onClick={() => { onChange(f); setOpen(false); }}
              className={`w-full text-left px-4 py-2 text-[13px] hover:bg-gray-50 transition-colors ${
                value === f ? 'text-[#0e7490] font-semibold' : 'text-gray-700'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ActivityFeed({ activities = [], loading = false }) {
  const [expandedId, setExpandedId] = useState(null);
  const [filter, setFilter] = useState('All activity types');
  const [showAll, setShowAll] = useState(false);

  const filtered = filter === 'All activity types'
    ? activities
    : activities.filter(a => a.type === filter);

  const PAGE_SIZE = 8;
  const visible = showAll ? filtered : filtered.slice(0, PAGE_SIZE);

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-gray-400 text-[20px]">rss_feed</span>
          <h3 className="font-semibold text-gray-800 text-sm">Activity Feed</h3>
          {activities.length > 0 && (
            <span className="text-[11px] text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
              {filtered.length}
            </span>
          )}
        </div>

        {/* Filter dropdown */}
        <FilterDropdown value={filter} onChange={setFilter} />
      </div>

      {/* Body */}
      {loading ? (
        <div className="space-y-0">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center gap-3 px-5 py-3.5 border-b border-gray-100 animate-pulse">
              <div className="w-4 h-4 bg-gray-100 rounded flex-shrink-0" />
              <div className="w-8 h-8 bg-gray-100 rounded-full flex-shrink-0" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3.5 bg-gray-100 rounded w-3/4" />
                <div className="h-2.5 bg-gray-100 rounded w-1/3" />
              </div>
              <div className="w-12 h-5 bg-gray-100 rounded flex-shrink-0" />
              <div className="w-12 h-3 bg-gray-100 rounded flex-shrink-0" />
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-32 text-gray-400 text-sm gap-1">
          <span className="material-symbols-outlined text-[32px]">inbox</span>
          No {filter === 'All activity types' ? '' : filter.toLowerCase() + ' '}activity yet
        </div>
      ) : (
        <>
          {visible.map((item, idx) => (
            <FeedRow
              key={item.id || idx}
              item={item}
              expanded={expandedId === (item.id || idx)}
              onToggle={() =>
                setExpandedId(prev =>
                  prev === (item.id || idx) ? null : (item.id || idx)
                )
              }
            />
          ))}

          {filtered.length > PAGE_SIZE && (
            <div className="px-5 py-3 border-t border-gray-100 text-center">
              <button
                onClick={() => setShowAll(v => !v)}
                className="text-[12px] text-[#0e7490] font-semibold hover:underline"
              >
                {showAll
                  ? 'Show less'
                  : `Show all ${filtered.length} activities ›`}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
