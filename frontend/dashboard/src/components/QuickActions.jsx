import { useState } from 'react';
import { api } from '../api.js';

export default function QuickActions({ stalledCount, onActionDone }) {
  const [loading, setLoading] = useState(null);
  const [toast, setToast]     = useState(null);

  async function trigger(name, apiFn) {
    setLoading(name);
    try {
      const res = await apiFn();
      setToast({ type: 'ok', msg: res.message || 'Done' });
      onActionDone && onActionDone();
    } catch (e) {
      setToast({ type: 'err', msg: e.message });
    } finally {
      setLoading(null);
      setTimeout(() => setToast(null), 3000);
    }
  }

  const actions = [
    { id: 'run',     icon: 'play_circle',        label: 'Trigger Run',   fn: api.runNow },
    { id: 'replies', icon: 'mark_email_unread',   label: 'Check Replies', fn: api.checkReplies, badge: null },
    { id: 'stalled', icon: 'pause_presentation',  label: 'Check Stalled', fn: api.checkStalled, badge: stalledCount > 0 ? stalledCount : null },
  ];

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">
      <h3 className="font-headline-sm text-headline-sm mb-lg">Quick Actions</h3>

      {toast && (
        <div className={`mb-sm px-md py-sm rounded text-[11px] font-bold ${
          toast.type === 'ok' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
        }`}>
          {toast.msg}
        </div>
      )}

      <div className="space-y-sm">
        {actions.map(a => (
          <button
            key={a.id}
            onClick={() => trigger(a.id, a.fn)}
            disabled={loading === a.id}
            className="w-full flex items-center justify-between p-md border border-outline-variant rounded-lg hover:bg-surface-container transition-all text-left disabled:opacity-60"
          >
            <div className="flex items-center gap-md">
              <span className="material-symbols-outlined text-primary">
                {loading === a.id ? 'refresh' : a.icon}
              </span>
              <span className="font-label-md">{a.label}</span>
            </div>
            <div className="flex items-center gap-xs">
              {a.badge && (
                <span className="bg-error text-white text-[10px] font-bold px-1.5 py-0.5 rounded">
                  {a.badge}
                </span>
              )}
              <span className="material-symbols-outlined text-outline">chevron_right</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
