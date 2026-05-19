import { useState, useEffect } from 'react';
import { api } from '../api.js';

// ── Stage config — matches HubSpot default deal pipeline ─────────────────────
const STAGES = [
  { id: 'appointmentscheduled', label: 'Interested',        color: 'bg-[#e5eeff] text-[#004395]' },
  { id: 'qualifiedtobuy',       label: 'Qualified',         color: 'bg-tertiary-container text-on-tertiary-container' },
  { id: 'presentationscheduled',label: 'Proposal Sent',     color: 'bg-secondary-container text-on-secondary-container' },
  { id: 'decisionmakerboughtin',label: 'Decision Pending',  color: 'bg-[#fff0c2] text-[#5c4200]' },
  { id: 'contractsent',         label: 'Contract Sent',     color: 'bg-[#ffd6cc] text-[#7a1f00]' },
  { id: 'closedwon',            label: 'Closed Won',        color: 'bg-[#d4f5e2] text-[#0a4d2a]' },
  { id: 'closedlost',           label: 'Closed Lost',       color: 'bg-error-container text-error' },
];

function stageLabel(stageId) {
  return STAGES.find(s => s.id === stageId)?.label || stageId || 'Unknown';
}
function stageColor(stageId) {
  return STAGES.find(s => s.id === stageId)?.color || 'bg-surface-container text-on-surface';
}

// ── Deal Card ─────────────────────────────────────────────────────────────────
function DealCard({ deal }) {
  const amount = deal.amount ? `$${Number(deal.amount).toLocaleString()}` : '—';
  const closeDate = deal.close_date
    ? new Date(deal.close_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : '—';

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-md space-y-sm hover:shadow-sm transition-shadow">
      <div className="flex justify-between items-start gap-sm">
        <p className="font-label-md font-bold text-on-surface leading-snug">{deal.name || 'Unnamed Deal'}</p>
        <span className={`shrink-0 px-xs py-[2px] rounded-full text-[10px] font-bold uppercase border border-current/20 ${stageColor(deal.stage)}`}>
          {stageLabel(deal.stage)}
        </span>
      </div>
      {deal.deal_type && (
        <p className="font-body-sm text-on-secondary-container">{deal.deal_type}</p>
      )}
      <div className="flex justify-between items-center pt-xs border-t border-outline-variant/40">
        <span className="font-label-md font-bold text-on-surface">{amount}</span>
        <span className="font-body-sm text-on-secondary-container">{closeDate}</span>
      </div>
    </div>
  );
}

// ── Stage Column ──────────────────────────────────────────────────────────────
function StageColumn({ stage, deals }) {
  const total = deals.reduce((s, d) => s + (Number(d.amount) || 0), 0);
  return (
    <div className="flex flex-col min-w-[220px] max-w-[260px] flex-shrink-0">
      <div className="flex justify-between items-center mb-md">
        <div>
          <h3 className="font-label-md font-bold text-on-surface">{stage.label}</h3>
          <p className="font-body-sm text-on-secondary-container">{deals.length} deal{deals.length !== 1 ? 's' : ''}</p>
        </div>
        {total > 0 && (
          <span className="font-label-md font-bold text-on-secondary-container">
            ${total.toLocaleString()}
          </span>
        )}
      </div>
      <div className="space-y-sm flex-1">
        {deals.length === 0 ? (
          <div className="border-2 border-dashed border-outline-variant rounded-lg p-lg text-center">
            <p className="font-body-sm text-on-secondary-container">No deals</p>
          </div>
        ) : (
          deals.map(d => <DealCard key={d.id} deal={d} />)
        )}
      </div>
    </div>
  );
}

// ── Deals Page ────────────────────────────────────────────────────────────────
export default function DealsPage() {
  const [deals, setDeals]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);
  const [filter, setFilter] = useState('open'); // open | all

  useEffect(() => {
    setLoading(true);
    api.deals()
      .then(d => { setDeals(d.deals || []); setError(null); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  // Filter: "open" hides closedwon + closedlost
  const visible = filter === 'open'
    ? deals.filter(d => d.stage !== 'closedwon' && d.stage !== 'closedlost')
    : deals;

  // Group by stage
  const byStage = {};
  for (const d of visible) {
    const s = d.stage || 'unknown';
    (byStage[s] = byStage[s] || []).push(d);
  }

  const totalPipeline = visible.reduce((s, d) => s + (Number(d.amount) || 0), 0);
  const wonDeals      = deals.filter(d => d.stage === 'closedwon');
  const wonValue      = wonDeals.reduce((s, d) => s + (Number(d.amount) || 0), 0);

  return (
    <div className="p-gutter space-y-gutter">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-md">
        <div>
          <h1 className="font-bold text-on-surface mb-xs" style={{fontSize:'32px'}}>Pipeline Board</h1>
          <p className="font-body-md text-on-secondary-container">
            Deals auto-created when leads reply · drag in HubSpot to advance stages
          </p>
        </div>
        <div className="flex items-center gap-xs bg-surface-container-lowest border border-outline-variant p-xs rounded-lg">
          {[['open','Open Deals'],['all','All Deals']].map(([v,l]) => (
            <button key={v} onClick={() => setFilter(v)}
              className={`px-md py-sm font-label-md rounded-md transition-colors ${filter===v ? 'bg-secondary-container text-on-secondary-container' : 'text-on-secondary-container hover:bg-surface-container-low'}`}>
              {l}
            </button>
          ))}
        </div>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-md">
        {[
          { label: 'Total Deals',    value: deals.length },
          { label: 'Open Pipeline',  value: `$${totalPipeline.toLocaleString()}` },
          { label: 'Closed Won',     value: wonDeals.length },
          { label: 'Won Value',      value: `$${wonValue.toLocaleString()}` },
        ].map(k => (
          <div key={k.label} className="bg-surface-container-lowest border border-outline-variant rounded-lg p-md">
            <p className="font-body-sm text-on-secondary-container uppercase tracking-wider mb-xs">{k.label}</p>
            <p className="font-bold text-on-surface" style={{fontSize:'24px'}}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Info banner */}
      <div className="bg-secondary-container/40 border border-secondary/20 rounded-lg px-lg py-md flex items-start gap-md">
        <span className="material-symbols-outlined text-on-secondary-container mt-[2px]" style={{fontSize:'20px'}}>info</span>
        <div className="font-body-sm text-on-secondary-container space-y-xs">
          <p><strong>How deals are created:</strong> When a lead replies to your sequence email, a deal is automatically created in HubSpot and set to <em>Interested</em> stage.</p>
          <p><strong>Weekly review:</strong> Open HubSpot → Deals → Board View. Drag stale deals forward or mark Closed Lost. Takes 15 minutes max.</p>
          <p><strong>Fill in amount + close date</strong> on each deal so your pipeline value is meaningful.</p>
        </div>
      </div>

      {/* Board */}
      {loading ? (
        <div className="flex items-center justify-center py-24">
          <span className="material-symbols-outlined animate-spin text-primary" style={{fontSize:'40px'}}>progress_activity</span>
        </div>
      ) : error ? (
        <div className="bg-error-container border border-error rounded-lg p-lg flex items-center gap-md">
          <span className="material-symbols-outlined text-error">warning</span>
          <div>
            <p className="font-label-md text-on-error-container font-bold">Could not load deals</p>
            <p className="font-body-sm text-on-error-container">{error} — make sure the backend is running.</p>
          </div>
        </div>
      ) : (
        <div className="overflow-x-auto pb-md">
          <div className="flex gap-lg" style={{minWidth: `${STAGES.length * 260}px`}}>
            {STAGES.map(stage => (
              <StageColumn
                key={stage.id}
                stage={stage}
                deals={byStage[stage.id] || []}
              />
            ))}
          </div>
        </div>
      )}

      {/* HubSpot link */}
      <div className="flex justify-end">
        <a
          href="https://app.hubspot.com/contacts/deals"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-sm text-primary font-label-md hover:underline"
        >
          <span className="material-symbols-outlined" style={{fontSize:'18px'}}>open_in_new</span>
          Open in HubSpot
        </a>
      </div>
    </div>
  );
}
