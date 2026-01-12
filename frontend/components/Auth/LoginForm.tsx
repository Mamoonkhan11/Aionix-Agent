'use client';

import { useState } from 'react';
import { useAuth } from '../../context/AuthProvider';

export default function LoginForm() {
  const { login } = useAuth();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({
    ...f, [e.target.name]: e.target.value
  }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    const res = await login(form.email, form.password);
    if (!res.success) setError(res.error);
    setLoading(false);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 w-80">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Email or Username</label>
        <input
          name="email"
          type="text"
          value={form.email}
          onChange={handleChange}
          required
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="your@email.com or username"
        />
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
        {loading ? "Signing In..." : "Sign In"}
      </button>
    </form>
  );
}

