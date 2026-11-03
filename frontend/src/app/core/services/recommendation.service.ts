import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { RecommendationResponse, EvaluationPayload } from '../models/recommendation.model';

@Injectable({
  providedIn: 'root',
})
export class RecommendationService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api/recommendations';

  list(): Observable<RecommendationResponse[]> {
    return this.http.get<RecommendationResponse[]>(this.baseUrl);
  }

  getById(id: number): Observable<RecommendationResponse> {
    return this.http.get<RecommendationResponse>(`${this.baseUrl}/${id}`);
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
}

