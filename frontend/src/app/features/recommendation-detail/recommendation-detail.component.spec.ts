import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { vi } from 'vitest';
import { RecommendationDetailComponent } from './recommendation-detail.component';
import { RecommendationService } from '../../core/services/recommendation.service';
import { RecommendationResponse } from '../../core/models/recommendation.model';

describe('RecommendationDetailComponent', () => {
  let component: RecommendationDetailComponent;
  let fixture: ComponentFixture<RecommendationDetailComponent>;

  const initialRec: RecommendationResponse = {
    id: 1,
    product_id: 10,
    recommended_quantity: 200,
    supplier_id: 2,
    requested_delivery_date: '2026-11-15',
    status: 'PENDING_APPROVAL',
    agent_decision: null,
    agent_suggested_quantity: null,
    agent_suggested_supplier_id: null,
    agent_reasoning: null,
    evaluated_at: null,
  };

  const evaluatedRec: RecommendationResponse = {
    ...initialRec,
    status: 'PENDING_APPROVAL',
    agent_decision: 'MODIFY',
    agent_suggested_quantity: 150,
    agent_suggested_supplier_id: 3,
    agent_reasoning: 'Excess inventory prevention.\n\nAlternative supplier offers shorter lead time.',
    evaluated_at: '2026-11-03T00:00:00Z',
  };

  const approvedRec: RecommendationResponse = {
    ...evaluatedRec,
    status: 'APPROVED',
  };

  const mockService = {
    getById: vi.fn(),
    runEvaluation: vi.fn(),
    approve: vi.fn(),
  };

  beforeEach(async () => {
    vi.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [RecommendationDetailComponent],
      providers: [
        provideRouter([]),
        { provide: RecommendationService, useValue: mockService },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              paramMap: {
                get: (key: string) => (key === 'id' ? '1' : null),
              },
            },
          },
        },
      ],
    }).compileComponents();
  });

  it('should load recommendation on init', () => {
    mockService.getById.mockReturnValue(of(initialRec));

    fixture = TestBed.createComponent(RecommendationDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.recommendation()?.id).toBe(1);
    expect(component.canApprove()).toBe(true);
  });

  it('should run evaluation and update recommendation details', () => {
    mockService.getById.mockReturnValue(of(initialRec));
    mockService.runEvaluation.mockReturnValue(of(evaluatedRec));

    fixture = TestBed.createComponent(RecommendationDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    component.onRunEvaluation();

    expect(mockService.runEvaluation).toHaveBeenCalledWith(1);
    expect(component.recommendation()?.agent_decision).toBe('MODIFY');
    expect(component.isQuantityModified()).toBe(true);
    expect(component.isSupplierModified()).toBe(true);
    expect(component.formattedReasoning().length).toBe(2);
  });

  it('should approve recommendation when status is PENDING_APPROVAL', () => {
    mockService.getById.mockReturnValue(of(evaluatedRec));
    mockService.approve.mockReturnValue(of(approvedRec));

    fixture = TestBed.createComponent(RecommendationDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.canApprove()).toBe(true);

    component.onApprove();

    expect(mockService.approve).toHaveBeenCalledWith(1);
    expect(component.recommendation()?.status).toBe('APPROVED');
    expect(component.canApprove()).toBe(false);
  });
});
