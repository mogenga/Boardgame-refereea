import React from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import './Layout.css';

function Layout() {
  return (
    <div className="layout">
      <nav className="navbar">
        <div className="navbar-brand">
          <span className="navbar-icon">🎲</span>
          <span className="navbar-title">桌游裁判助手</span>
        </div>
        <div className="navbar-links">
          <NavLink to="/rules" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            规则库
          </NavLink>
          <NavLink to="/sessions" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            游戏大厅
          </NavLink>
        </div>
      </nav>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;
