import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Gauge,
  AlertCircle,
  Network,
  Binary,
  CheckCircle2,
  FlaskConical,
  Sliders,
  LucideIcon,
} from 'lucide-react';

interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
}

interface NavGroup {
  group: string;
  items: NavItem[];
}

export const Sidebar: React.FC = () => {
  const navigationGroups: NavGroup[] = [
    {
      group: 'Overview',
      items: [
        { label: 'Overview', to: '/', icon: Gauge },
        { label: 'Incidents', to: '/incidents', icon: AlertCircle },
        { label: 'Service Map', to: '/services', icon: Network },
      ],
    },
    {
      group: 'Intelligence',
      items: [
        { label: 'Model Intelligence', to: '/models', icon: Binary },
        { label: 'AI Evaluation', to: '/evaluations', icon: CheckCircle2 },
      ],
    },
    {
      group: 'Operations',
      items: [
        { label: 'Fault Lab', to: '/fault-lab', icon: FlaskConical },
        { label: 'Settings', to: '/settings', icon: Sliders },
      ],
    },
  ];

  return (
    <aside className="w-56 bg-bg-sidebar border-r border-border-subtle flex flex-col justify-between shrink-0 h-screen select-none font-sans">
      <div className="flex flex-col">
        {/* Brand header */}
        <div className="h-12 px-4 flex items-center justify-between border-b border-border-subtle">
          <div className="flex items-center gap-2">
            {/* Minimal technical logo */}
            <div className="w-5 h-5 rounded-sm bg-text-primary text-bg-app flex items-center justify-center font-mono font-bold text-[11px] leading-none tracking-tighter">
              W
            </div>
            <span className="font-medium text-text-primary text-xs tracking-tight">Wingman AI</span>
          </div>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-bg-surface border border-border-subtle text-text-muted">
            v1.0.0
          </span>
        </div>

        {/* Navigation list */}
        <div className="p-2 space-y-4 pt-3">
          {navigationGroups.map((group) => (
            <div key={group.group} className="space-y-0.5">
              <div className="px-2.5 pb-1 text-[10px] font-mono uppercase tracking-widest text-text-muted">
                {group.group}
              </div>
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `flex items-center gap-2 px-2.5 py-1.5 rounded-sm text-xs transition-colors ${
                        isActive
                          ? 'bg-bg-raised text-text-primary font-medium border border-border-primary'
                          : 'text-text-secondary hover:text-text-primary hover:bg-bg-surface'
                      }`
                    }
                  >
                    <Icon size={14} className="opacity-70 stroke-[1.75]" />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Bottom connectivity status */}
      <div className="p-3 border-t border-border-subtle">
        <div className="px-2.5 py-2 rounded-sm bg-bg-surface border border-border-subtle flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-status-sage" />
            <span className="text-text-secondary text-[11px] font-mono">Telemetry Active</span>
          </div>
          <span className="text-text-muted text-[10px] font-mono">0.0.0.0:8008</span>
        </div>
      </div>
    </aside>
  );
};
