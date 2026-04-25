import React from 'react'
import { clsx } from 'clsx'

export default function Button({ children, variant = 'default', className = '', ...props }){
  const base = 'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2'
  const variants = {
    default: 'bg-indigo-600 text-white hover:bg-indigo-500 focus:ring-indigo-300 px-4 py-2',
    ghost: 'bg-transparent text-indigo-600 px-2 py-1',
    secondary: 'bg-white border text-gray-700 px-3 py-1.5'
  }
  return (
    <button className={clsx(base, variants[variant] ?? variants.default, className)} {...props}>
      {children}
    </button>
  )
}
