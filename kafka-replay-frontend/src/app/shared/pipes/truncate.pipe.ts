import { Pipe, PipeTransform } from '@angular/core';

/**
 * Truncate pipe
 * Truncates text to specified length with ellipsis
 */
@Pipe({
  name: 'appTruncate',
  standalone: true,
})
export class TruncatePipe implements PipeTransform {
  transform(value: string | null | undefined, length: number = 50): string {
    if (!value) {
      return '';
    }

    if (value.length <= length) {
      return value;
    }

    return value.substring(0, length) + '...';
  }
}
