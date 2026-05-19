function KPICard({ label, value, trend, trendUp, alert }) {
  return (
    <div className={`bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm ${alert ? 'border-l-4 border-l-error' : ''}`}>
      <p className="font-label-md text-on-secondary-fixed-variant mb-sm">{label}</p>
      <div className="flex items-center justify-between">
        <h2 className={`font-headline-lg text-headline-lg ${alert ? 'text-error' : ''}`}>{value ?? '—'}</h2>
        {trend !== undefined && (
          <span className={`flex items-center font-label-md ${alert ? 'text-error' : trendUp ? 'text-emerald-600' : 'text-on-secondary-container'}`}>
            {alert
              ? <><span className="material-symbols-outlined text-[16px]">warning</span> Critical</>
              : trendUp
                ? <><span className="material-symbols-outlined text-[16px]">trending_up</span>{trend}</>
                : <span>{trend}</span>
            }
          </span>
        )}
      </div>
    </div>
  );
}

export default function KPICards({ kpi }) {
  return (
    <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-gutter">
      <KPICard label="Total Outreach"     value={kpi?.total_contacts}   trend="All time"  trendUp={false} />
      <KPICard label="Active Sequences"   value={kpi?.active_sequences} trend="Current"   trendUp={false} />
      <KPICard label="Replied"            value={kpi?.replied_24h}      trend="Replied"   trendUp={true}  />
      <KPICard label="Stalled Leads"      value={kpi?.stalled_leads}    alert={(kpi?.stalled_leads ?? 0) > 0} />
    </section>
  );
}
