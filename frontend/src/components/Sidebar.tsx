import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  AlertTriangle,
  Network,
  Cpu,
  FlaskConical,
  CheckCircle2,
  Settings,
  ShieldAlert,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { label: 'Overview', to: '/', icon: LayoutDashboard },
    { label: 'Incidents', to: '/incidents', icon: AlertTriangle },
    { label: 'Service Map', to: '/services', icon: Network },
    { label: 'Model Intelligence', to: '/models', icon: Cpu },
    { label: 'AI Evaluation', to: '/evaluations', icon: CheckCircle2 },
    { label: 'Fault Lab', to: '/fault-lab', icon: FlaskConical },
    { label: 'Settings', to: '/settings', icon: Settings },
  ];

  return (
    <aside className="w-60 bg-bg-sidebar border-r border-border-subtle flex flex-col justify-between shrink-0 h-screen select-none">
      <div>
        {/* Brand */}
        <div className="h-14 px-4 flex items-center border-b border-border-subtle gap-2.5">
          <div className="w-6 h-6 rounded bg-accent/20 border border-accent/40 flex items-center justify-center text-accent">
            <ShieldAlert size={15} />
          </div>
          <div>
            <span className="font-semibold text-text-primary text-sm tracking-tight">Wingman AI</span>
            <span className="ml-1.5 text-[10px] uppercase font-mono px-1 py-0.5 rounded bg-border-subtle text-text-muted">
              v1.0
            </span>
          </div>
        </div>

        {/* Navigation links */}
        <div className="p-2 space-y-0.5">
          <div className="px-3 py-1.5 text-[11px] font-medium tracking-wider uppercase text-text-muted">
            Platform
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-3 py-2 rounded text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-bg-raised text-accent border border-border-strong'
                      : 'text-text-secondary hover:text-text-primary hover:bg-bg-surface'
                  }`
                }
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </div>
      </div>

      {/* Footer status pill */}
      <div className="p-3 border-t border-border-subtle">
        <div className="bg-bg-surface border border-border-subtle rounded p-2.5 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-status-success animate-pulse" />
            <span className="text-text-secondary text-[11px] font-mono">Simulator Online</span>
          </div>
          <span className="text-text-muted text-[10px] font-mono">20 RPS</span>
        </div>
      </div>
    </aside>
  );
};
