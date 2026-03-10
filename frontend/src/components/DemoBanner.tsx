import { useState, useEffect } from 'react';
import { Info, X } from 'lucide-react';

const DEMO_BANNER_KEY = 'planweaver_demo_dismissed';

export function DemoBanner() {
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    const wasDismissed = localStorage.getItem(DEMO_BANNER_KEY) === 'true';
    setDismissed(wasDismissed);
  }, []);

  function handleDismiss() {
    setDismissed(true);
    localStorage.setItem(DEMO_BANNER_KEY, 'true');
  }

  if (dismissed) return null;

  return (
    <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-2">
      <div className="container mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-amber-200 text-sm">
          <Info size={16} className="shrink-0" />
          <span>
            <strong>Demo Mode</strong> — Rate limited to 10 plans/hour. 
            Some features may be restricted.
          </span>
        </div>
        <button
          onClick={handleDismiss}
          className="shrink-0 p-1 text-amber-400 hover:text-amber-200 transition-colors"
          aria-label="Dismiss"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  );
}
