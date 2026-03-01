import { Injectable } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';

export interface AppError {
  id: string;
  message: string;
  code?: string;
  timestamp: Date;
  details?: unknown;
}

/**
 * Global error handler service
 * Manages application-wide error state and notifications
 */
@Injectable({
  providedIn: 'root',
})
export class ErrorHandlerService {
  private errors$ = new BehaviorSubject<AppError[]>([]);

  constructor() {}

  /**
   * Get observable of current errors
   */
  getErrors(): Observable<AppError[]> {
    return this.errors$.asObservable();
  }

  /**
   * Add an error
   */
  addError(message: string, code?: string, details?: unknown): void {
    const error: AppError = {
      id: `${Date.now()}-${Math.random()}`,
      message,
      code,
      timestamp: new Date(),
      details,
    };

    const currentErrors = this.errors$.value;
    this.errors$.next([...currentErrors, error]);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      this.removeError(error.id);
    }, 5000);
  }

  /**
   * Handle HTTP error
   */
  handleHttpError(error: HttpErrorResponse): void {
    let message = 'An unexpected error occurred';
    let code = `HTTP_${error.status}`;

    if (error.error instanceof ErrorEvent) {
      message = error.error.message;
    } else if (error.error?.detail) {
      message = error.error.detail;
    } else if (error.statusText) {
      message = error.statusText;
    }

    this.addError(message, code, error);
  }

  /**
   * Remove an error by ID
   */
  removeError(id: string): void {
    const currentErrors = this.errors$.value;
    this.errors$.next(currentErrors.filter((e) => e.id !== id));
  }

  /**
   * Clear all errors
   */
  clearErrors(): void {
    this.errors$.next([]);
  }
}
