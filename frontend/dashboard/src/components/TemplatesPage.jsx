import { useState, useEffect, useCallback } from 'react';
import { api } from '../api.js';

const DAY_LABELS = { 1: 'Day 1', 3: 'Day 3', 7: 'Day 7', 14: 'Day 14', null: 'Re-engage' };
const TYPE_LABELS = { bulk_liquid: 'Bulk Liquid', private_label: 'Private Label', general: 'General', all: 'All Types' };
const TYPE_COLORS = {
  bulk_liquid:   'bg-blue-50 text-blue-700 border-blue-200',
  private_label: 'bg-purple-50 text-purple-700 border-purple-200',
  general:       'bg-gray-50 text-gray-600 border-gray-200',
  all:           'bg-amber-50 text-amber-700 border-amber-200',
};

export default function TemplatesPage() {
  const [templates,  setTemplates]  = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [selected,   setSelected]   = useState(null); // key string
  const [editSubject,setEditSubject]= useState('');
  const [editBody,   setEditBody]   = useState('');
  const [dirty,      setDirty]      = useState(false);
  const [saving,     setSaving]     = useState(false);
  const [saveMsg,    setSaveMsg]    = useState('');
  const [preview,    setPreview]    = useState(null);
  const [previewName,setPreviewName]= useState('Alex');
  const [previewExpo,setPreviewExpo]= useState('FoodEx 2025');
  const [showPreview,setShowPreview]= useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await api.getTemplates();
      setTemplates(d.templates || []);
      if (!selected && d.templates?.length) {
        const first = d.templates[0];
        setSelected(first.key);
        setEditSubject(first.subject);
        setEditBody(first.body);
      }
    } catch (e) {
      console.warn('Templates load failed:', e.message);
    } finally {
      setLoading(false);
    }
  }, [selected]);

  useEffect(() => { load(); }, []);

  function selectTemplate(tpl) {
    if (dirty && !confirm('You have unsaved changes. Discard?')) return;
    setSelected(tpl.key);
    setEditSubject(tpl.subject);
    setEditBody(tpl.body);
    setDirty(false);
    setSaveMsg('');
    setShowPreview(false);
    setPreview(null);
  }

  async function handleSave() {
    if (!selected) return;
    setSaving(true);
    try {
      await api.saveTemplate(selected, editSubject, editBody);
      setTemplates(prev => prev.map(t =>
        t.key === selected ? { ...t, subject: editSubject, body: editBody } : t
      ));
      setDirty(false);
      setSaveMsg('✓ Saved');
      setTimeout(() => setSaveMsg(''), 3000);
    } catch (e) {
      setSaveMsg('✗ Save failed');
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    if (!selected) return;
    if (!confirm('Reset to original Python template?')) return;
    try {
      await api.resetTemplate(selected);
      await load();
      setSaveMsg('✓ Reset to default');
      setTimeout(() => setSaveMsg(''), 3000);
    } catch (e) {
      setSaveMsg('✗ Reset failed');
    }
  }

  async function handlePreview() {
    if (!selected) return;
    try {
      const d = await api.previewTemplate(selected, previewName, previewExpo);
      setPreview(d);
      setShowPreview(true);
    } catch (e) {
      setPreview({ subject: 'Error', body: e.message });
      setShowPreview(true);
    }
  }

  const currentTpl = templates.find(t => t.key === selected);

  return (
    <div className="p-gutter space-y-gutter">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-bold text-on-surface" style={{fontSize:'28px'}}>Email Templates</h2>
          <p className="font-body-sm text-on-secondary-container mt-xs">
            Edit your sequence email templates. Changes are applied to the next send.
          </p>
        </div>
        <button onClick={load}
          className="flex items-center gap-sm px-md py-sm rounded-lg border border-outline-variant hover:bg-surface-container font-label-md text-on-surface transition-colors">
          <span className="material-symbols-outlined text-base">refresh</span>
          Reload
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64 text-on-secondary-container font-body-sm">
          <span className="material-symbols-outlined animate-spin mr-sm">refresh</span>
          Loading templates…
        </div>
      ) : (
        <div className="flex gap-gutter items-start">

          {/* Left sidebar — template list */}
          <div className="w-64 flex-shrink-0 bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
            <div className="px-md py-sm bg-surface-container-low border-b border-outline-variant">
              <p className="font-label-md text-on-secondary-container">{templates.length} templates</p>
            </div>
            <div className="divide-y divide-outline-variant max-h-[70vh] overflow-y-auto">
              {templates.map(tpl => (
                <button key={tpl.key} onClick={() => selectTemplate(tpl)}
                  className={`w-full text-left px-md py-sm transition-colors ${selected === tpl.key ? 'bg-secondary-container' : 'hover:bg-surface-container'}`}>
                  <div className="font-label-md text-on-surface font-bold">
                    {DAY_LABELS[tpl.day] ?? 'Re-engage'}
                  </div>
                  <span className={`inline-block mt-xs px-xs py-[2px] rounded border text-[10px] font-semibold ${TYPE_COLORS[tpl.lead_type]}`}>
                    {TYPE_LABELS[tpl.lead_type]}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Right — editor */}
          <div className="flex-1 space-y-md">
            {currentTpl && (
              <div className="flex items-center gap-sm flex-wrap">
                <span className="font-bold text-on-surface" style={{fontSize:'18px'}}>
                  {DAY_LABELS[currentTpl.day]} — {TYPE_LABELS[currentTpl.lead_type]}
                </span>
                <span className={`px-sm py-xs rounded-full border font-label-md ${TYPE_COLORS[currentTpl.lead_type]}`}>
                  {currentTpl.key}
                </span>
                {dirty && <span className="font-label-md text-amber-600">● Unsaved changes</span>}
                {saveMsg && <span className="font-label-md text-emerald-600">{saveMsg}</span>}
              </div>
            )}

            {/* Subject */}
            <div>
              <label className="font-label-md text-on-secondary-container block mb-xs">Subject line</label>
              <input
                type="text"
                value={editSubject}
                onChange={e => { setEditSubject(e.target.value); setDirty(true); }}
                className="w-full px-md py-sm border border-outline-variant rounded-lg bg-surface-container-lowest font-body-md text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="Email subject…"
              />
            </div>

            {/* Body */}
            <div>
              <label className="font-label-md text-on-secondary-container block mb-xs">
                Body <span className="text-[10px] text-on-secondary-container ml-sm">Use {'{{first_name}}'} and {'{{expo_name}}'} as placeholders</span>
              </label>
              <textarea
                value={editBody}
                onChange={e => { setEditBody(e.target.value); setDirty(true); }}
                rows={16}
                className="w-full px-md py-sm border border-outline-variant rounded-lg bg-surface-container-lowest font-body-md text-on-surface focus:outline-none focus:ring-1 focus:ring-primary resize-y"
                placeholder="Email body…"
                style={{fontFamily:'JetBrains Mono, monospace', fontSize:'13px', lineHeight:'1.6'}}
              />
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-md flex-wrap">
              <button onClick={handleSave} disabled={!dirty || saving}
                className="flex items-center gap-sm px-lg py-sm bg-primary text-on-primary rounded-lg font-label-md hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-all">
                <span className="material-symbols-outlined text-base">save</span>
                {saving ? 'Saving…' : 'Save Template'}
              </button>
              <button onClick={handleReset}
                className="flex items-center gap-sm px-md py-sm border border-outline-variant rounded-lg font-label-md text-on-secondary-container hover:bg-surface-container transition-colors">
                <span className="material-symbols-outlined text-base">restart_alt</span>
                Reset to Default
              </button>

              {/* Preview controls */}
              <div className="flex items-center gap-sm ml-auto flex-wrap">
                <input type="text" value={previewName} onChange={e => setPreviewName(e.target.value)}
                  placeholder="First name" className="px-sm py-xs border border-outline-variant rounded font-body-sm text-on-surface bg-surface-container-lowest w-28 focus:outline-none focus:ring-1 focus:ring-primary" />
                <input type="text" value={previewExpo} onChange={e => setPreviewExpo(e.target.value)}
                  placeholder="Expo name" className="px-sm py-xs border border-outline-variant rounded font-body-sm text-on-surface bg-surface-container-lowest w-36 focus:outline-none focus:ring-1 focus:ring-primary" />
                <button onClick={handlePreview}
                  className="flex items-center gap-sm px-md py-sm border border-outline-variant rounded-lg font-label-md text-on-surface hover:bg-surface-container transition-colors">
                  <span className="material-symbols-outlined text-base">visibility</span>
                  Preview
                </button>
              </div>
            </div>

            {/* Preview panel */}
            {showPreview && preview && (
              <div className="border border-outline-variant rounded-xl overflow-hidden">
                <div className="px-lg py-sm bg-surface-container-low border-b border-outline-variant flex items-center justify-between">
                  <span className="font-label-md text-on-secondary-container">Preview — as {previewName} would see it</span>
                  <button onClick={() => setShowPreview(false)} className="text-on-secondary-container hover:text-on-surface">
                    <span className="material-symbols-outlined text-base">close</span>
                  </button>
                </div>
                <div className="p-lg bg-surface-container-lowest">
                  <div className="mb-md">
                    <span className="font-label-md text-on-secondary-container">Subject: </span>
                    <span className="font-body-md font-bold text-on-surface">{preview.subject}</span>
                  </div>
                  <pre className="font-body-sm text-on-surface whitespace-pre-wrap leading-relaxed" style={{fontFamily:'Inter, sans-serif'}}>
                    {preview.body}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
