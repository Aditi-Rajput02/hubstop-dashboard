import { NavLink, useNavigate } from 'react-router-dom';

const navItems = [
  { to: '/dashboard', icon: 'dashboard',    label: 'Dashboard' },
  { to: '/contacts',  icon: 'group',        label: 'Contacts'  },
  { to: '/sequences', icon: 'account_tree', label: 'Sequences' },
  { to: '/templates', icon: 'mail',         label: 'Templates' },
  { to: '/analytics', icon: 'insights',     label: 'Analytics' },
  { to: '/deals',     icon: 'view_kanban',  label: 'Pipeline'  },
  { to: '/logs',      icon: 'list_alt',     label: 'Logs'      },
];

export default function Sidebar() {
  const navigate = useNavigate();

  return (
    <aside className="h-screen w-64 fixed left-0 top-0 bg-surface-container-lowest border-r border-outline-variant flex flex-col p-md gap-sm z-50">
      {/* Logo */}
      <div className="flex items-center gap-sm mb-lg px-xs">
        <div className="w-8 h-8 bg-primary-container rounded flex items-center justify-center">
          <span className="material-symbols-outlined text-[20px] text-on-primary-container">account_tree</span>
        </div>
        <div>
          <h1 className="font-headline-sm text-headline-sm font-bold text-on-surface">Automation Hub</h1>
          <p className="font-label-md text-[10px] text-on-secondary-container">System Active</p>
        </div>
      </div>

      {/* New Sequence Button */}
      <button
        onClick={() => navigate('/sequences')}
        className="bg-primary text-on-primary font-label-md py-sm px-md rounded-lg mb-md flex items-center justify-center gap-sm cursor-pointer active:opacity-80 transition-all"
      >
        <span className="material-symbols-outlined">add</span>
        New Sequence
      </button>

      {/* Nav Links */}
      <nav className="flex flex-col gap-xs flex-grow">
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-md p-md rounded-lg transition-all duration-200 text-left w-full ${
                isActive
                  ? 'bg-secondary-container text-on-secondary-container font-bold'
                  : 'text-on-secondary-fixed-variant hover:bg-surface-container'
              }`
            }
          >
            <span className="material-symbols-outlined">{item.icon}</span>
            <span className="font-label-md">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Bottom Links */}
      <div className="border-t border-outline-variant pt-md flex flex-col gap-xs">
        <a href="#" className="text-on-secondary-fixed-variant flex items-center gap-md p-md hover:bg-surface-container transition-all duration-200 rounded-lg">
          <span className="material-symbols-outlined">support_agent</span>
          <span className="font-label-md">Support</span>
        </a>
        <a href="#" className="text-on-secondary-fixed-variant flex items-center gap-md p-md hover:bg-surface-container transition-all duration-200 rounded-lg">
          <span className="material-symbols-outlined">manage_accounts</span>
          <span className="font-label-md">Account</span>
        </a>
      </div>
    </aside>
  );
}
