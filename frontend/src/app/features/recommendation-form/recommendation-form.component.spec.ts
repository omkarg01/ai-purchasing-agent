import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter, Router } from '@angular/router';
import { of } from 'rxjs';
import { vi } from 'vitest';
import { RecommendationFormComponent } from './recommendation-form.component';
import { RecommendationService } from '../../core/services/recommendation.service';
import { ProductLookup, SupplierLookup, RecommendationResponse } from '../../core/models/recommendation.model';

describe('RecommendationFormComponent', () => {
  let component: RecommendationFormComponent;
  let fixture: ComponentFixture<RecommendationFormComponent>;
  let router: Router;

  const mockProducts: ProductLookup[] = [
    { id: 1, name: 'Precision Widget', sku: 'SKU-001' },
  ];

  const mockSuppliers: SupplierLookup[] = [
    { id: 2, supplier_name: 'Acme Supplies' },
  ];

  const mockCreated: RecommendationResponse = {
    id: 10,
    product_id: 1,
    supplier_id: 2,
    recommended_quantity: 200,
    requested_delivery_date: '2026-11-15',
    status: 'PENDING_APPROVAL',
    agent_decision: null,
    agent_suggested_quantity: null,
    agent_suggested_supplier_id: null,
    agent_reasoning: null,
    evaluated_at: null,
  };

  const mockService = {
    getProducts: vi.fn(),
    getSuppliers: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
  };

  beforeEach(async () => {
    vi.clearAllMocks();
    mockService.getProducts.mockReturnValue(of(mockProducts));
    mockService.getSuppliers.mockReturnValue(of(mockSuppliers));

    await TestBed.configureTestingModule({
      imports: [RecommendationFormComponent],
      providers: [
        provideRouter([]),
        { provide: RecommendationService, useValue: mockService },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              paramMap: {
                get: (key: string) => null, // Create mode by default
              },
            },
          },
        },
      ],
    }).compileComponents();

    router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate');
  });

  it('should initialize in create mode and load catalog data', () => {
    fixture = TestBed.createComponent(RecommendationFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.isEditMode()).toBe(false);
    expect(component.products().length).toBe(1);
    expect(component.suppliers().length).toBe(1);
  });

  it('should submit new recommendation in create mode and redirect to detail', () => {
    mockService.create.mockReturnValue(of(mockCreated));

    fixture = TestBed.createComponent(RecommendationFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    component.formData.productId = 1;
    component.formData.supplierId = 2;
    component.formData.quantity = 200;
    component.formData.deliveryDate = '2026-11-15';

    component.onSubmit();

    expect(mockService.create).toHaveBeenCalledWith({
      product_id: 1,
      supplier_id: 2,
      recommended_quantity: 200,
      requested_delivery_date: '2026-11-15',
    });
    expect(router.navigate).toHaveBeenCalledWith(['/recommendations', 10]);
  });
});

