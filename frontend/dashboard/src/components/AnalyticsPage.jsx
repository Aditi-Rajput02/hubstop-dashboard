import { useState } from 'react';

// ── Metric Card ───────────────────────────────────────────────────────────────
function MetricCard({ label, value, delta, deltaUp, sub }) {
  return (
    <div className="bg-surface-container-lowest border border-outline-variant p-lg rounded-lg">
      <div className="flex justify-between items-start mb-sm">
        <span className="font-body-sm font-bold text-on-secondary-container uppercase tracking-wider">{label}</span>
        <span className={`flex items-center font-bold font-label-md px-xs rounded ${deltaUp ? 'bg-tertiary-fixed text-on-tertiary-container' : 'bg-error-container text-error border border-error/20'}`}>
          <span className="material-symbols-outlined" style={{fontSize:'16px'}}>{deltaUp ? 'arrow_upward' : 'arrow_downward'}</span>
          {delta}
        </span>
      </div>
      <div className="font-bold text-on-surface mb-xs" style={{fontSize:'32px',lineHeight:'40px'}}>{value}</div>
      <p className="font-body-sm text-on-secondary-container">{sub}</p>
    </div>
  );
}

// ── Conversion Bar ────────────────────────────────────────────────────────────
function ConversionBar({ name, pct, label }) {
  return (
    <div>
      <div className="flex justify-between items-center mb-xs">
        <span className="font-label-md text-on-surface">{name}</span>
        <span className="font-label-md font-bold">{label}</span>
      </div>
      <div className="w-full h-2 bg-surface-container rounded-full overflow-hidden">
        <div className="h-full bg-primary rounded-full" style={{width:`${pct}%`}} />
      </div>
    </div>
  );
}

const CHART_BARS = [
  { sent: 60, reply: 10 }, { sent: 75, reply: 15 }, { sent: 85, reply: 20 },
  { sent: 65, reply: 12 }, { sent: 90, reply: 25 }, { sent: 70, reply: 18 }, { sent: 80, reply: 22 },
];
const CHART_LABELS = ['01 Oct','08 Oct','15 Oct','22 Oct','29 Oct'];

const CONVERSIONS = [
  { name: 'Enterprise Outbound Alpha',  pct: 82, label: '12.4%' },
  { name: 'SMB Nurture Phase 2',        pct: 54, label: '8.1%'  },
  { name: 'Re-activation Campaign Q3',  pct: 38, label: '5.7%'  },
  { name: 'Inbound Lead Fast-Track',    pct: 95, label: '18.9%' },
];

const LOG_ROWS = [
  { initials:'JD', name:'Julianne Davis', role:'CTO @ TechFlow',    seq:'Enterprise Outbound Alpha', status:'Meeting Booked', statusCls:'bg-[#d8e2ff] text-[#004395] border-[#004395]/20', time:'2 mins ago'  },
  { initials:'MK', name:'Marcus Kane',    role:'Director @ Nexus Ltd.', seq:'SMB Nurture Phase 2',   status:'Replied',        statusCls:'bg-secondary-container text-on-secondary-container border-secondary/20', time:'14 mins ago' },
  { initials:'AL', name:'Aria Ling',      role:'Founder @ Bloom AI', seq:'Inbound Lead Fast-Track',  status:'Meeting Booked', statusCls:'bg-[#d8e2ff] text-[#004395] border-[#004395]/20', time:'1 hour ago'  },
];

export default function AnalyticsPage() {
  const [range, setRange] = useState('7d');

  return (
    <div className="p-gutter space-y-gutter">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-md">
        <div>
          <h1 className="font-bold text-on-surface mb-xs" style={{fontSize:'32px'}}>Analytics Dashboard</h1>
          <p className="font-body-md text-on-secondary-container">Systematic breakdown of your CRM automation performance.</p>
        </div>
        <div className="flex items-center gap-xs bg-surface-container-lowest p-xs rounded-lg border border-outline-variant">
          {[['7d','Last 7 Days'],['30d','Last 30 Days']].map(([v,l]) => (
            <button key={v} onClick={() => setRange(v)}
              className={`px-md py-sm font-label-md rounded-md transition-colors ${range===v ? 'bg-secondary-container text-on-secondary-container' : 'text-on-secondary-container hover:bg-surface-container-low'}`}>
              {l}
            </button>
          ))}
          <div className="w-px h-6 bg-outline-variant mx-xs" />
          <button className="flex items-center gap-xs px-md py-sm font-label-md text-on-secondary-container hover:bg-surface-container-low rounded-md transition-colors">
            <span className="material-symbols-outlined" style={{fontSize:'18px'}}>calendar_today</span>
            Custom Range
          </button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-lg">
        <MetricCard label="Total Outreach"     value="42,891" delta="12.4%" deltaUp={true}  sub="Unique emails delivered across 14 sequences." />
        <MetricCard label="Avg. Reply Rate"    value="8.42%"  delta="2.1%"  deltaUp={true}  sub="Interaction benchmark vs. 7.9% previous period." />
        <MetricCard label="Stalled Lead Ratio" value="3.1%"   delta="0.8%"  deltaUp={false} sub="Active leads with no interaction in >5 business days." />
      </div>

      {/* Charts Bento */}
      <div className="grid grid-cols-12 gap-lg">
        {/* Line Chart */}
        <div className="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-outline-variant p-lg rounded-lg">
          <div className="flex justify-between items-center mb-lg">
            <div>
              <h3 className="font-headline-sm text-on-surface">Emails Sent vs. Replies</h3>
              <p className="font-body-sm text-on-secondary-container">Temporal performance mapping over the last 30 days.</p>
            </div>
            <div className="flex items-center gap-md">
              <div className="flex items-center gap-xs"><span className="w-3 h-3 rounded-full bg-primary" /><span className="font-label-md text-on-secondary-container">Sent</span></div>
              <div className="flex items-center gap-xs"><span className="w-3 h-3 rounded-full bg-on-tertiary-container" /><span className="font-label-md text-on-secondary-container">Replies</span></div>
            </div>
          </div>
          <div className="h-64 flex items-end gap-xs w-full relative pt-4">
            <div className="absolute inset-0 flex flex-col justify-between py-xs pointer-events-none">
              {[0,1,2,3].map(i => <div key={i} className="border-t border-outline-variant/30 w-full h-px" />)}
            </div>
            {CHART_BARS.map((b,i) => (
              <div key={i} className="flex-1 flex flex-col justify-end gap-1 px-1">
                <div className="w-full bg-primary opacity-20 rounded-t" style={{height:`${b.sent}%`}} />
                <div className="w-full bg-on-tertiary-container rounded-t" style={{height:`${b.reply}%`}} />
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-sm font-label-md text-on-secondary-container px-1">
            {CHART_LABELS.map(l => <span key={l}>{l}</span>)}
          </div>
        </div>

        {/* Donut Chart */}
        <div className="col-span-12 lg:col-span-4 bg-surface-container-lowest border border-outline-variant p-lg rounded-lg">
          <h3 className="font-headline-sm text-on-surface mb-sm">Lead Quality Breakdown</h3>
          <p className="font-body-sm text-on-secondary-container mb-lg">Qualification metrics based on ICP matching.</p>
          <div className="relative w-48 h-48 mx-auto mb-lg">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="15.9" fill="transparent" stroke="#e5eeff" strokeWidth="4" />
              <circle cx="18" cy="18" r="15.9" fill="transparent" stroke="#001a42" strokeWidth="4" strokeDasharray="65 100" strokeLinecap="round" />
              <circle cx="18" cy="18" r="15.9" fill="transparent" stroke="#565e74" strokeWidth="4" strokeDasharray="25 100" strokeDashoffset="-65" strokeLinecap="round" />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-bold text-on-surface" style={{fontSize:'20px'}}>65%</span>
              <span className="font-label-md text-on-secondary-container">Tier 1</span>
            </div>
          </div>
          <div className="space-y-sm">
            {[
              { color:'bg-tertiary-container', label:'High Intent (Tier 1)', val:'27.8k' },
              { color:'bg-surface-tint',       label:'Mid Market (Tier 2)',  val:'10.7k' },
              { color:'bg-surface-container',  label:'Researching (Tier 3)', val:'4.3k'  },
            ].map(r => (
              <div key={r.label} className="flex items-center justify-between">
                <div className="flex items-center gap-sm">
                  <span className={`w-2 h-2 rounded-full ${r.color}`} />
                  <span className="font-label-md text-on-surface">{r.label}</span>
                </div>
                <span className="font-label-md font-bold">{r.val}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Conversion Rates */}
        <div className="col-span-12 bg-surface-container-lowest border border-outline-variant p-lg rounded-lg">
          <div className="flex justify-between items-center mb-lg">
            <div>
              <h3 className="font-headline-sm text-on-surface">Conversion Rates by Sequence</h3>
              <p className="font-body-sm text-on-secondary-container">Tracking "Meeting Booked" status per automated workflow.</p>
            </div>
            <button className="flex items-center gap-sm text-primary font-label-md hover:underline">
              View Full Report <span className="material-symbols-outlined" style={{fontSize:'18px'}}>open_in_new</span>
            </button>
          </div>
          <div className="space-y-lg">
            {CONVERSIONS.map(c => <ConversionBar key={c.name} name={c.name} pct={c.pct} label={c.label} />)}
          </div>
        </div>
      </div>

      {/* Conversion Events Table */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
        <div className="p-lg border-b border-outline-variant">
          <h3 className="font-headline-sm text-on-surface">System Logs: Conversion Events</h3>
          <p className="font-body-sm text-on-secondary-container">Real-time monitoring of lead progression across sequences.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-surface-container-low font-label-md text-on-secondary-container">
              <tr>
                {['Lead / Contact','Active Sequence','Status','Last Activity','Action'].map((h,i) => (
                  <th key={h} className={`px-lg py-md ${i===4?'text-right':''}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant font-body-md">
              {LOG_ROWS.map(r => (
                <tr key={r.name} className="hover:bg-surface-container-low transition-colors">
                  <td className="px-lg py-md">
                    <div className="flex items-center gap-md">
                      <div className="h-8 w-8 rounded-full bg-primary-fixed text-primary flex items-center justify-center font-bold text-[10px]">{r.initials}</div>
                      <div>
                        <div className="text-on-surface font-bold">{r.name}</div>
                        <div className="font-body-sm text-on-secondary-container">{r.role}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-lg py-md text-on-secondary-container">{r.seq}</td>
                  <td className="px-lg py-md">
                    <span className={`px-sm py-xs rounded-full border font-label-md text-[10px] uppercase ${r.statusCls}`}>{r.status}</span>
                  </td>
                  <td className="px-lg py-md text-on-secondary-container">{r.time}</td>
                  <td className="px-lg py-md text-right">
                    <button className="material-symbols-outlined text-on-secondary-container hover:text-primary transition-colors">more_vert</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
