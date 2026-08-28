// implements utils
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

// implements cn
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
