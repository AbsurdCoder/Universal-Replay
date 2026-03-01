import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpErrorResponse,
} from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ErrorHandlerService } from '../services/error-handler.service';

/**
 * HTTP error interceptor
 * Catches all HTTP errors and delegates to error handler service
 */
@Injectable()
export class ErrorInterceptor implements HttpInterceptor {
  constructor(private errorHandler: ErrorHandlerService) {}

  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    return next.handle(request).pipe(
      catchError((error: HttpErrorResponse) => {
        this.errorHandler.handleHttpError(error);
        return throwError(() => error);
      })
    );
  }
}
