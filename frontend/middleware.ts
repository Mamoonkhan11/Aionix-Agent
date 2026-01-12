import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import jwtDecode from 'jwt-decode'

// List of routes that require authentication
const protectedRoutes = [
  '/dashboard',
  '/dashboard/overview',
  '/dashboard/tasks',
  '/dashboard/insights',
  '/dashboard/reports',
  '/dashboard/settings',
]

// Minimal role-based example (expand as needed)
function hasRequiredRole(token: string, route: string): boolean {
  try {
    const data: any = jwtDecode(token)
    if (route.startsWith('/dashboard/settings')) {
      return data.role === 'admin'
    }
    // stakeholder and admin have access to most dashboard areas
    return ['stakeholder', 'admin'].includes(data.role)
  } catch (e) {
    return false
  }
}

export function middleware(request: NextRequest) {
  // Disable middleware authentication checks for now
  // Authentication is handled client-side by AuthProvider
  // TODO: Implement proper server-side authentication middleware if needed
  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*', '/settings/:path*'],
}

