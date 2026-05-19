export default function TopBar({ engineOnline }) {
  return (
    <header className="w-full top-0 sticky bg-surface border-b border-outline-variant flex justify-between items-center h-16 px-gutter z-40">
      <div className="flex items-center gap-lg">
        <span className="font-headline-md text-headline-md font-bold text-on-surface">Sequence Automator</span>
        <div className="relative flex items-center">
          <span className="material-symbols-outlined absolute left-3 text-outline text-[18px]">search</span>
          <input
            className="bg-surface-container-low border-none rounded-full py-2 pl-10 pr-4 text-body-sm w-64 focus:outline-none focus:ring-1 focus:ring-primary"
            placeholder="Search sequences..."
            type="text"
          />
        </div>
      </div>

      <div className="flex items-center gap-md">
        {/* Engine status */}
        <div className="flex items-center gap-xs mr-md">
          <span className={`w-2 h-2 rounded-full ${engineOnline ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></span>
          <span className="font-label-md text-on-secondary-fixed-variant">
            Engine: {engineOnline ? 'Online' : 'Offline'}
          </span>
        </div>

        <button className="text-on-secondary-fixed-variant hover:bg-surface-container-low p-2 rounded-full transition-colors">
          <span className="material-symbols-outlined">notifications</span>
        </button>
        <button className="text-on-secondary-fixed-variant hover:bg-surface-container-low p-2 rounded-full transition-colors">
          <span className="material-symbols-outlined">settings</span>
        </button>
        <button className="text-on-secondary-fixed-variant hover:bg-surface-container-low p-2 rounded-full transition-colors">
          <span className="material-symbols-outlined">help</span>
        </button>

        <div className="w-8 h-8 rounded-full overflow-hidden ml-md border border-outline-variant bg-primary-container flex items-center justify-center">
          <span className="material-symbols-outlined text-on-primary-container text-[18px]">person</span>
        </div>
      </div>
    </header>
  );
}
