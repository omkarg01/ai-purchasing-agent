import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { RecommendationService } from './recommendation.service';
import {
  RecommendationResponse,
  ProductLookup,
  SupplierLookup,
} from '../models/recommendation.model';

describe('RecommendationService', () => {
  let service: RecommendationService;
  let httpTesting: HttpTestingController;

  const mockRecommendation: RecommendationResponse = {
    id: 1,
    product_id: 101,
    recommended_quantity: 200,
    supplier_id: 5,
    requested_delivery_date: '2026-11-10',
    status: 'PENDING_APPROVAL',
    agent_decision: 'ACCEPT',
    agent_suggested_quantity: 200,
    agent_suggested_supplier_id: 5,
    agent_reasoning: 'Stockout risk mitigated.',
    evaluated_at: '2026-11-03T00:00:00Z',
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        RecommendationService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(RecommendationService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('should list all recommendations', () => {
    service.list().subscribe((data) => {
      expect(data.length).toBe(1);
      expect(data[0].id).toBe(1);
    });

    const req = httpTesting.expectOne('/api/recommendations');
    expect(req.request.method).toBe('GET');
    req.flush([mockRecommendation]);
  });

  it('should get recommendation by id', () => {
    service.getById(1).subscribe((data) => {
      expect(data.id).toBe(1);
      expect(data.status).toBe('PENDING_APPROVAL');
    });

    const req = httpTesting.expectOne('/api/recommendations/1');
    expect(req.request.method).toBe('GET');
    req.flush(mockRecommendation);
  });

  it('should create recommendation', () => {
    service.create({
      product_id: 101,
      supplier_id: 5,
      recommended_quantity: 200,
      requested_delivery_date: '2026-11-10',
    }).subscribe((data) => {
      expect(data.id).toBe(1);
    });

    const req = httpTesting.expectOne('/api/recommendations');
    expect(req.request.method).toBe('POST');
    expect(req.request.body.recommended_quantity).toBe(200);
    req.flush(mockRecommendation);
  });

  it('should update recommendation', () => {
    const updated = { ...mockRecommendation, recommended_quantity: 350 };
    service.update(1, { recommended_quantity: 350 }).subscribe((data) => {
      expect(data.recommended_quantity).toBe(350);
    });

    const req = httpTesting.expectOne('/api/recommendations/1');
    expect(req.request.method).toBe('PUT');
    expect(req.request.body.recommended_quantity).toBe(350);
    req.flush(updated);
  });

  it('should fetch product catalog', () => {
    const mockProducts: ProductLookup[] = [{ id: 1, name: 'Widget A', sku: 'SKU-01' }];
    service.getProducts().subscribe((data) => {
      expect(data.length).toBe(1);
      expect(data[0].sku).toBe('SKU-01');
    });

    const req = httpTesting.expectOne('/api/catalog/products');
    expect(req.request.method).toBe('GET');
    req.flush(mockProducts);
  });

  it('should fetch supplier catalog', () => {
    const mockSuppliers: SupplierLookup[] = [{ id: 2, supplier_name: 'Acme Corp' }];
    service.getSuppliers().subscribe((data) => {
      expect(data.length).toBe(1);
      expect(data[0].supplier_name).toBe('Acme Corp');
    });

    const req = httpTesting.expectOne('/api/catalog/suppliers');
    expect(req.request.method).toBe('GET');
    req.flush(mockSuppliers);
  });

  it('should run evaluation with deterministic engine', () => {
    service.runEvaluation(1).subscribe((data) => {
      expect(data.agent_decision).toBe('ACCEPT');
    });

    const req = httpTesting.expectOne('/api/recommendations/1/run-evaluation');
    expect(req.request.method).toBe('POST');
    req.flush(mockRecommendation);
  });

  it('should approve recommendation', () => {
    const approved = { ...mockRecommendation, status: 'APPROVED' };
    service.approve(1).subscribe((data) => {
      expect(data.status).toBe('APPROVED');
    });

    const req = httpTesting.expectOne('/api/recommendations/1/approve');
    expect(req.request.method).toBe('POST');
    req.flush(approved);
  });
});
