# Aionix AI Dashboard Starter

This is a production-grade Next.js 14 SaaS dashboard starter for enterprise AI admin use-cases.

## Features

- Next.js 14 App Router, TypeScript
- TailwindCSS (with dark mode, accessible, scalable UI)
- ESLint & Prettier
- JWT authentication with FastAPI backend (role-based: admin/stakeholder)
- Route protection and UI-level RBAC
- Secure token handling (HttpOnly cookies)
- Modular, enterprise folder structure
- Real-time, accessible, and responsive dashboard UI
- Error handling (toast notifications, empty states, loaders)
- Security best practices: CSP, secure cookies, API fallback, code splitting

## Getting Started

1. **Install dependencies:**
   ```bash
   npm install
   # or
   yarn
   ```
2. **Configure environment:**
   - Copy `.env.example` to `.env.local` and fill in your API URLs/secrets.
3. **Run the app:**
   ```bash
   npm run dev
   ```

## Project Structure

- `/app` – Next.js App Router pages/layouts (login, dashboard, sections)
- `/components` – UI, Auth, Dashboard, charts, utilities
- `/context` – React context (AuthProvider)
- `/lib` – API calls and helpers (auth, dashboard, rbac)
- `/hooks` – Custom hooks (auth, toast, websocket)
- `/styles` – Tailwind and global CSS
- `/middleware.ts` – RBAC and token protection

## How Authentication Works

- **Login/Signup** connects to FastAPI backend for JWT-issued tokens.
- JWT is stored in an HttpOnly cookie for security.
- Frontend decodes and checks role for RBAC (admin, stakeholder).
- Backend must enforce roles as well for API protection.

## RBAC (Role-Based Access)

- Pages and components are protected based on role (see `middleware.ts` and Sidebar).
- Admin-only settings. Only admins can see and use certain actions/UI.

## Security & Performance

- CSP headers set in Next.js config.
- API rate limit errors handled gracefully.
- Code-split (lazy load) charts, insights, etc.
- Strong typing and linting everywhere.

## Customization

Use, swap, or extend all stubs/components as you build out your SaaS dashboard.
Customize the dashboard's cards, charts, real-time view, forms, and error handling!

---
MIT © 2026 Aionix

