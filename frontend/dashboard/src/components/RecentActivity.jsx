// ── Helpers ───────────────────────────────────────────────────────────────────

function timeAgoLabel(isoStr) {
  if (!isoStr) return 'recently';
  const ms = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 1)   return 'just now';
  if (mins < 60)  return `${mins} minute${mins !== 1 ? 's' : ''} ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)   return `${hrs} hour${hrs !== 1 ? 's' : ''} ago`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return 'yesterday';
  return `${days} days ago`;
}

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }) {
  if (!status) return null;

  // Normalize to uppercase for matching
  const upper = status.toUpperCase();

  // HubSpot hs_lead_status values → teal badge
  const tealStatuses = ['LEAD', 'NEW', 'OPEN', 'IN PROGRESS', 'OPEN DEAL', 'CONNECTED', 'FOLLOWED-UP', 'ACTIVE'];
  // Gray/neutral badges
  const grayStatuses = ['DRAFT', 'UNQUALIFIED', 'ATTEMPTED TO CONTACT', 'BAD TIMING'];
  // Green badges
  const greenStatuses = ['REPLIED', 'CLOSED WON', 'CLOSED'];
  // Amber badges
  const amberStatuses = ['STALLED', 'APPOINTMENT SCHEDULED'];
  // Purple badges
  const purpleStatuses = ['COMPLETE', 'QUALIFIED TO BUY'];

  let cls = 'bg-[#0e7490] text-white'; // default teal for any HubSpot lead status
  if (greenStatuses.some(s => upper.includes(s))) {
    cls = 'bg-emerald-600 text-white';
  } else if (amberStatuses.some(s => upper.includes(s))) {
    cls = 'bg-amber-500 text-white';
  } else if (purpleStatuses.some(s => upper.includes(s))) {
    cls = 'bg-purple-600 text-white';
  } else if (grayStatuses.some(s => upper.includes(s))) {
    cls = 'bg-gray-200 text-gray-700';
  } else if (upper === 'NEW' || upper === 'ACTIVE' || tealStatuses.some(s => upper.includes(s))) {
    cls = 'bg-[#0e7490] text-white';
  }

  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wide ${cls}`}>
      {status}
    </span>
  );
}

// ── Type label ────────────────────────────────────────────────────────────────

function typeLabel(item) {
  if (item.type === 'contact') return 'Contact';
  if (item.type === 'deal')    return 'Deal';
  if (item.type === 'email')   return 'Marketing email';
  return 'Activity';
}

// ── Single card ───────────────────────────────────────────────────────────────

function ActivityCard({ item }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-2 min-w-0 hover:shadow-md transition-shadow cursor-default">
      {/* Top row: type + status badge */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[12px] text-gray-400 font-medium">{typeLabel(item)}</span>
        {item.status && <StatusBadge status={item.status} />}
      </div>

      {/* Name */}
      <div className="flex-1">
        <p className="font-bold text-gray-800 text-sm leading-snug line-clamp-2">{item.name}</p>
      </div>

      {/* Footer: who + when */}
      <p className="text-[11px] text-gray-400">
        You edited {timeAgoLabel(item.last_modified)}
      </p>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function RecentActivity({ items = [], loading = false }) {
  // Show at most 4 cards
  const visible = items.slice(0, 4);

  return (
    <div className="space-y-3">
      {/* Section header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-gray-400 text-[20px]">history</span>
          <h3 className="font-semibold text-gray-700 text-sm">Recent activity</h3>
        </div>
      </div>

      {/* Cards grid */}
      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-xl p-4 h-28 animate-pulse">
              <div className="h-3 bg-gray-100 rounded w-1/2 mb-3" />
              <div className="h-4 bg-gray-100 rounded w-3/4 mb-2" />
              <div className="h-3 bg-gray-100 rounded w-1/3" />
            </div>
          ))}
        </div>
      ) : visible.length === 0 ? (
        <div className="text-sm text-gray-400 py-4 text-center">No recent activity found.</div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {visible.map((item, idx) => (
            <ActivityCard key={item.id || idx} item={item} />
          ))}
        </div>
      )}

      {/* See all link */}
      {items.length > 0 && (
        <div className="text-right">
          <span className="text-[12px] text-[#0e7490] font-semibold cursor-pointer hover:underline">
            See all recent activity ›
          </span>
        </div>
      )}
    </div>
  );
}
