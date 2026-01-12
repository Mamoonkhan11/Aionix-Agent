import React from 'react';

export default function Button({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={
        'btn-primary px-4 py-2 rounded font-medium bg-primary text-white hover:bg-blue-600 transition ' +
        (props.className || '')
      }
    >
      {children}
    </button>
  );
}

