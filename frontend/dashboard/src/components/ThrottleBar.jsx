export default function ThrottleBar({ throttle }) {
  const sent = throttle?.sent_today ?? 0;
  const cap  = throttle?.daily_cap  ?? 50;
  const pct  = cap > 0 ? Math.round((sent / cap) * 100) : 0;
  const open = throttle?.window_open ?? false;

  return (
    <section className="bg-surface-container-lowest border border-outline-variant rounded-xl p-lg flex items-center justify-between shadow-sm">
      <div className="flex items-center gap-xl">
        <div>
          <p className="font-label-md text-on-secondary-fixed-variant mb-xs">Throttle Control</p>
          <div className="flex items-end gap-sm">
            <span className="font-headline-lg text-headline-lg">{pct}%</span>
            <span className="font-body-sm text-on-secondary-container mb-1.5">Capacity Usage</span>
          </div>
        </div>
        <div className="h-12 w-[1px] bg-outline-variant"></div>
        <div>
          <p className="font-label-md text-on-secondary-fixed-variant mb-xs">Email Throughput</p>
          <div className="flex items-center gap-md">
            <div className="w-48 h-2 bg-surface-container rounded-full overflow-hidden">
              <div
                className="bg-primary h-full transition-all duration-500"
                style={{ width: `${pct}%` }}
              ></div>
            </div>
            <span className="font-label-md text-on-surface">{sent}/{cap} sent</span>
          </div>
          <p className="font-body-sm text-on-secondary-container mt-xs">
            Warmup Day {throttle?.warmup_day ?? 1} · {throttle?.sender_time ?? '—'}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-md">
        <div className={`border px-md py-sm rounded-lg flex items-center gap-sm ${
          open
            ? 'bg-emerald-50 border-emerald-200'
            : 'bg-amber-50 border-amber-200'
        }`}>
          <span className={`w-2 h-2 rounded-full ${open ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
          <span className={`font-label-md ${open ? 'text-emerald-700' : 'text-amber-700'}`}>
            {open ? 'WINDOW: OPEN' : 'WINDOW: CLOSED'}
          </span>
        </div>
        <button className="bg-surface border border-outline-variant text-on-surface font-label-md px-md py-sm rounded hover:bg-surface-container transition-colors">
          Adjust Limits
        </button>
      </div>
    </section>
  );
}
