// ---------------------------------------------------------------------------
// Common / shared TypeScript types for NEX Payroll frontend
// ---------------------------------------------------------------------------

/** Generic paginated API response matching backend PaginatedResponse[T] */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

/** Common query parameters for paginated list endpoints */
export interface PaginationParams {
  skip?: number;
  limit?: number;
}

/** API error response shape */
export interface ApiError {
  detail: string | ValidationError[];
}

/** FastAPI validation error detail item */
export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}
