import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Helper para combinar classes CSS, lidando com:
 * - Valores condicionais (true/false)
 * - Arrays / objetos
 * - Conflitos de classes do Tailwind (twMerge)
 */
export function cn(...classValues: ClassValue[]): string {
  return twMerge(clsx(classValues));
}
