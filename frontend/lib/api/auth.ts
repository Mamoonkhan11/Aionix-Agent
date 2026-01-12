const API_BASE_URL = '/api';

export const login = async (email: string, password: string) => {
  try {
    console.log('Making login request to:', `${API_BASE_URL}/auth/login/json`);
    console.log('Request body:', { username: email, password });

    const res = await fetch(`${API_BASE_URL}/auth/login/json`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username: email, password }),
    });

    console.log('Response status:', res.status);
    console.log('Response ok:', res.ok);

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Login failed' }));
      console.log('Error response:', errorData);
      return { success: false, error: errorData.detail || 'Invalid credentials' };
    }

    const data = await res.json();
    console.log('Success response:', data);

    // Store auth token
    if (data.access_token) {
      localStorage.setItem('auth_token', data.access_token);
      console.log('Token stored in localStorage');
    }

    return { success: true, user: data.user };
  } catch (error) {
    console.error('Login error:', error);
    return { success: false, error: 'Network error. Please check if the backend is running.' };
  }
};

export const logout = async () => {
  try {
    localStorage.removeItem('auth_token');
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    });
  } catch (error) {
    console.error('Logout error:', error);
  }
};

export const me = async () => {
  try {
    const token = localStorage.getItem('auth_token');
    if (!token) return null;

    const res = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`
      },
      credentials: 'include',
    });

    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    console.error('Auth check error:', error);
    return null;
  }
};

