import { Pipe, PipeTransform } from '@angular/core';

/**
 * Date format pipe
 * Formats ISO date strings to readable format
 */
@Pipe({
  name: 'appDateFormat',
  standalone: true,
})
export class DateFormatPipe implements PipeTransform {
  transform(value: string | null | undefined, format: 'short' | 'long' = 'short'): string {
    if (!value) {
      return '-';
    }

    try {
      const date = new Date(value);
      if (isNaN(date.getTime())) {
        return '-';
      }

      if (format === 'short') {
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      } else {
        return date.toLocaleString();
      }
    } catch {
      return '-';
    }
  }
}
