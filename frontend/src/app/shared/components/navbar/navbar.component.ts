import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [RouterLink],
  template: `
    <header class="navbar">
      <div class="navbar-container">
        <a routerLink="/" class="brand">
          <div class="brand-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
              <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
              <line x1="12" y1="22.08" x2="12" y2="12"></line>
            </svg>
          </div>
          <div class="brand-text">
            <span class="brand-title">AI Purchasing Agent</span>
            <span class="brand-subtitle">Decision Support & Evaluation</span>
          </div>
        </a>
        <nav class="nav-links">
          <a routerLink="/dashboard" class="nav-link" routerLinkActive="active">Dashboard</a>
          <span class="system-badge">Deterministic Engine v1</span>
        </nav>
      </div>
    </header>
  `,
  styles: [`
    .navbar {
      background-color: #0f172a;
      border-bottom: 1px solid #1e293b;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .navbar-container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 0.75rem 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      text-decoration: none;
      color: #f8fafc;
    }
    .brand-icon {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: linear-space-gradient, #2563eb;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
    }
    .brand-icon svg {
      width: 20px;
      height: 20px;
    }
    .brand-text {
      display: flex;
      flex-direction: column;
    }
    .brand-title {
      font-weight: 700;
      font-size: 1.05rem;
      line-height: 1.2;
      color: #f1f5f9;
    }
    .brand-subtitle {
      font-size: 0.75rem;
      color: #94a3b8;
    }
    .nav-links {
      display: flex;
      align-items: center;
      gap: 1.25rem;
    }
    .nav-link {
      color: #cbd5e1;
      text-decoration: none;
      font-size: 0.9rem;
      font-weight: 500;
      padding: 0.4rem 0.8rem;
      border-radius: 6px;
      transition: background-color 0.15s ease, color 0.15s ease;
    }
    .nav-link:hover, .nav-link.active {
      color: #ffffff;
      background-color: #1e293b;
    }
    .system-badge {
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.25rem 0.6rem;
      border-radius: 9999px;
      background-color: #1e1b4b;
      color: #818cf8;
      border: 1px solid #3730a3;
    }
  `]
})
export class NavbarComponent {}

