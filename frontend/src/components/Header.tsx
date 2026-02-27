import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Activity, History, PlusCircle } from 'lucide-react';
import { cn } from '../utils';

export const Header: React.FC = () => {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'New Plan', icon: PlusCircle },
    { path: '/history', label: 'History', icon: History },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/30 bg-surface-muted/65 backdrop-blur-2xl">
      <div className="container mx-auto flex h-20 items-center justify-between px-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2 group">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-teal-400 text-slate-950 shadow-xl shadow-primary/25 transition-all duration-300 group-hover:scale-105 group-hover:rotate-3">
            <Activity size={18} />
          </div>
          <span className="text-xl font-heading font-bold tracking-tight text-white">
            Plan<span className="text-primary">Weaver</span>
          </span>
        </Link>

        <nav className="flex items-center gap-2 rounded-2xl border border-border/35 bg-surface/70 p-1.5">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-2 px-3 sm:px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300",
                location.pathname === item.path
                  ? "bg-primary text-slate-950 shadow-md shadow-primary/30"
                  : "text-text-muted hover:bg-white/5 hover:text-white"
              )}
            >
              <item.icon size={16} />
              <span className="hidden sm:inline">{item.label}</span>
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-4">
          <div className="h-2.5 w-2.5 rounded-full bg-success animate-pulse shadow-[0_0_14px_rgba(34,197,94,0.6)]" />
          <span className="hidden md:inline text-xs font-semibold text-success uppercase tracking-widest">
            System Online
          </span>
        </div>
      </div>
    </header>
  );
};
