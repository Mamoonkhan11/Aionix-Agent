import React from 'react';

export default function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input {...props} className={
      'input px-3 py-2 border rounded bg-gray-50 dark:bg-zinc-900 focus:outline-none focus:border-primary ' +
      (props.className || '')
    } />
  );
}

