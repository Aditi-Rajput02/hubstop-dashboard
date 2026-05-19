import { useEffect, useRef } from 'react';

function colorLine(line) {
  if (!line) return { color: 'text-slate-500', level: '' };
  const u = line.toUpperCase();
  if (u.includes('ERROR') || u.includes('FAILED') || u.includes('CRITICAL'))
    return { color: 'text-red-400',    level: 'ERROR' };
  if (u.includes('WARN'))
    return { color: 'text-amber-400',  level: 'WARN' };
  if (u.includes('INFO') || u.includes('SENT') || u.includes('REPLIED') || u.includes('SUCCESS'))
    return { color: 'text-emerald-400', level: 'INFO' };
  if (u.includes('DEBUG') || u.includes('WORK') || u.includes('SMTP') || u.includes('API'))
    return { color: 'text-blue-400',   level: 'WORK' };
  return { color: 'text-slate-300',   level: '' };
}

function parseTimestamp(line) {
  // Try to extract [HH:MM:SS] or YYYY-MM-DD HH:MM:SS
  const m1 = line.match(/\[(\d{2}:\d{2}:\d{2})\]/);
  if (m1) return { ts: m1[1], rest: line.replace(m1[0], '').trim() };
  const m2 = line.match(/(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/);
  if (m2) return { ts: m2[1].split(' ')[1], rest: line.replace(m2[0], '').trim() };
  return { ts: null, rest: line };
}

export default function LogTerminal({ lines }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [lines]);

  return (
    <section className="col-span-12">
      <div className="bg-slate-950 rounded-xl overflow-hidden shadow-xl">
        {/* Terminal header */}
        <div className="px-lg py-sm bg-slate-900 border-b border-slate-800 flex justify-between items-center">
          <div className="flex items-center gap-md">
            <div className="flex gap-xs">
              <div className="w-2.5 h-2.5 rounded-full bg-red-500/50"></div>
              <div className="w-2.5 h-2.5 rounded-full bg-amber-500/50"></div>
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/50"></div>
            </div>
            <h3 className="font-label-md text-slate-400">SYSTEM_LOG_OUTPUT</h3>
          </div>
          <div className="flex items-center gap-md">
            <span className="font-code-sm text-[10px] text-slate-500">
              {lines?.length ?? 0} lines
            </span>
            <button className="material-symbols-outlined text-slate-500 hover:text-white text-[18px]">
              filter_list
            </button>
          </div>
        </div>

        {/* Log lines */}
        <div className="p-lg font-code-sm text-code-sm text-slate-300 space-y-xs overflow-y-auto max-h-64 log-terminal">
          {(!lines || lines.length === 0) ? (
            <div className="text-slate-500 italic">No log entries yet...</div>
          ) : (
            lines.map((line, i) => {
              const { ts, rest } = parseTimestamp(line);
              const { color, level } = colorLine(line);
              return (
                <div key={i} className="flex gap-md">
                  {ts && <span className="text-slate-600 shrink-0">[{ts}]</span>}
                  {level && <span className={`${color} shrink-0`}>{level}</span>}
                  <span className={color}>{rest}</span>
                </div>
              );
            })
          )}
          {/* Blinking cursor */}
          <div className="flex gap-md border-t border-slate-900 pt-xs mt-xs">
            <span className="text-white animate-pulse">_</span>
            <span className="text-slate-500">Waiting for next scheduled trigger...</span>
          </div>
          <div ref={bottomRef} />
        </div>
      </div>
    </section>
  );
}
