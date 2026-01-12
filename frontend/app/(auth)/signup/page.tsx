'use client';

import Link from 'next/link';
import SignupForm from '../../../components/Auth/SignupForm';

export default function SignupPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">Aionix</h1>
            <div className="w-16 h-1 bg-blue-600 mx-auto mb-4"></div>
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Create your account
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Join Aionix Agent - Your Autonomous AI Knowledge Worker
          </p>
        </div>

        <SignupForm />

        <div className="text-center">
          <p className="text-sm text-gray-600">
            Already have an account?{' '}
            <Link
              href="/login"
              className="font-medium text-blue-600 hover:text-blue-500 transition-colors"
            >
              Sign in here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

