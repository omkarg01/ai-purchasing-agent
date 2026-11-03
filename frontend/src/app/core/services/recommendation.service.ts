import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  RecommendationResponse,
  RecommendationCreatePayload,
  RecommendationUpdatePayload,
  ProductLookup,
  SupplierLookup,
  EvaluationPayload,
  EvaluationHistoryItem,
} from '../models/recommendation.model';

@Injectable({
  providedIn: 'root',
})
export class RecommendationService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api/recommendations';
  private readonly catalogUrl = '/api/catalog';

  list(): Observable<RecommendationResponse[]> {
    return this.http.get<RecommendationResponse[]>(this.baseUrl);
  }

  getById(id: number): Observable<RecommendationResponse> {
    return this.http.get<RecommendationResponse>(`${this.baseUrl}/${id}`);
  }

  create(payload: RecommendationCreatePayload): Observable<RecommendationResponse> {
    return this.http.post<RecommendationResponse>(this.baseUrl, payload);
  }

  update(id: number, payload: RecommendationUpdatePayload): Observable<RecommendationResponse> {
    return this.http.put<RecommendationResponse>(`${this.baseUrl}/${id}`, payload);
  }

  runEvaluation(id: number): Observable<RecommendationResponse> {
    return this.http.post<RecommendationResponse>(`${this.baseUrl}/${id}/run-evaluation`, {});
  }

  approve(id: number): Observable<RecommendationResponse> {
    return this.http.post<RecommendationResponse>(`${this.baseUrl}/${id}/approve`, {});
  }

  evaluateCustom(id: number, payload: EvaluationPayload): Observable<RecommendationResponse> {
    return this.http.post<RecommendationResponse>(`${this.baseUrl}/${id}/evaluate`, payload);
  }

  getHistory(id: number): Observable<EvaluationHistoryItem[]> {
    return this.http.get<EvaluationHistoryItem[]>(`${this.baseUrl}/${id}/history`);
  }

  getProducts(): Observable<ProductLookup[]> {
    return this.http.get<ProductLookup[]>(`${this.catalogUrl}/products`);
  }

  getSuppliers(productId?: number | null): Observable<SupplierLookup[]> {
    const url = productId
      ? `${this.catalogUrl}/suppliers?product_id=${productId}`
      : `${this.catalogUrl}/suppliers`;
    return this.http.get<SupplierLookup[]>(url);
  }
}
