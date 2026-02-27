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
    <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-bg/80 backdrop-blur-md">
      <div className="container mx-auto flex h-16 items-center justify-between px-6">
        <Link to="/" className="flex items-center gap-2 group">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-white shadow-lg shadow-primary/20 transition-transform group-hover:scale-110">
            <Activity size={18} />
          </div>
          <span className="text-xl font-bold tracking-tight text-white italic">
            Plan<span className="text-primary not-italic">Weaver</span>
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-2 px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                location.pathname === item.path
                  ? "bg-primary/10 text-primary"
                  : "text-text-muted hover:bg-white/5 hover:text-white"
              )}
            >
              <item.icon size={16} />
              <span className="hidden sm:inline">{item.label}</span>
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-4">
          <div className="h-2 w-2 rounded-full bg-success animate-pulse" />
          <span className="hidden md:inline text-xs font-medium text-success uppercase tracking-widest">
            System Online
          </span>
        </div>
      </div>
    </header>
  );
};
