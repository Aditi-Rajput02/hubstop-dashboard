export default function EngineStatus({ throttle, engineOnline }) {
  const sent = throttle?.sent_today ?? 0;
  const cap  = throttle?.daily_cap  ?? 50;
  const pct  = cap > 0 ? Math.round((sent / cap) * 100) : 0;

  return (
    <div className="bg-primary-container text-white rounded-xl p-lg shadow-sm">
      <div className="flex justify-between items-start mb-md">
        <div>
          <h3 className="font-headline-sm text-headline-sm text-white">Automation Engine</h3>
          <p className="font-body-sm opacity-70">
            {throttle?.sender_time ? `Local time: ${throttle.sender_time}` : 'Checking status...'}
          </p>
        </div>
        <span className={`px-sm py-xs rounded text-[10px] font-bold ${
          engineOnline ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
        }`}>
          {engineOnline ? 'STABLE' : 'OFFLINE'}
        </span>
      </div>

      <div className="space-y-sm">
        <div className="flex justify-between text-body-sm">
          <span className="opacity-80">HubSpot API</span>
          <span className={engineOnline ? 'text-emerald-400' : 'text-red-400'}>
            {engineOnline ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        <div className="flex justify-between text-body-sm">
          <span className="opacity-80">Send Window</span>
          <span className={throttle?.window_open ? 'text-emerald-400' : 'text-amber-400'}>
            {throttle?.window_open ? 'Open' : 'Closed'}
          </span>
        </div>
        <div className="flex justify-between text-body-sm">
          <span className="opacity-80">Daily Quota</span>
          <span className="opacity-90">{sent}/{cap} emails</span>
        </div>
        <div className="w-full h-1 bg-white/10 rounded-full mt-md">
          <div
            className="bg-emerald-500 h-full rounded-full transition-all duration-500"
            style={{ width: `${pct}%` }}
          ></div>
        </div>
      </div>
    </div>
  );
}
