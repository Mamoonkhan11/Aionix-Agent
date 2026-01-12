'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function SignupForm() {
  const router = useRouter();
  const [form, setForm] = useState({
    email: '',
    username: '',
    first_name: '',
    last_name: '',
    password: '',
    confirm: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({
    ...f, [e.target.name]: e.target.value
  }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (form.password !== form.confirm) {
      setError('Passwords do not match');
      return;
    }

    if (form.password.length < 6) {
      setError('Password must be at least 6 characters long');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: form.email,
          username: form.username,
          first_name: form.first_name,
          last_name: form.last_name,
          password: form.password
        }),
      });

      if (res.ok) {
        router.push('/login?message=Account created successfully. Please log in.');
      } else {
        const data = await res.json().catch(() => ({ detail: 'Signup failed' }));
        setError(data.detail || 'Signup failed');
      }
    } catch (error) {
      console.error('Signup error:', error);
      setError('Network error. Please check if the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 w-80">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
        <input
          name="email"
          type="email"
          value={form.email}
          onChange={handleChange}
          required
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="your@email.com"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
        <input
          name="username"
          type="text"
          value={form.username}
          onChange={handleChange}
          required
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="username"
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
          <input
            name="first_name"
            type="text"
            value={form.first_name}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="John"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
          <input
            name="last_name"
            type="text"
            value={form.last_name}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Doe"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
        <input
          name="password"
          type="password"
          value={form.password}
          onChange={handleChange}
          required
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="••••••••"
          minLength={6}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Confirm Password</label>
        <input
          name="confirm"
          type="password"
          value={form.confirm}
          onChange={handleChange}
          required
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="••••••••"
        />
      </div>

      {error && (
        <div className="text-red-600 bg-red-50 border border-red-200 rounded-md p-3 text-sm">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? 'Creating Account...' : 'Sign Up'}
      </button>
    </form>
  );
}

