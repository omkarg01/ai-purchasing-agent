import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { vi } from 'vitest';
import { RecommendationDetailComponent } from './recommendation-detail.component';
import { RecommendationService } from '../../core/services/recommendation.service';
import { EvaluationHistoryItem, RecommendationResponse } from '../../core/models/recommendation.model';

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

  const mockHistory: EvaluationHistoryItem[] = [
    {
      id: 1,
      recommendation_id: 1,
      evaluation_sequence: 1,
      evaluated_quantity: 200,
      evaluated_supplier_id: 2,
      evaluated_supplier_name: 'Acme Corp',
      agent_decision: 'MODIFY',
      explanation: 'Modify order to 150 units.',
      evaluated_at: '2026-11-03T00:00:00Z',
    },
  ];

  const mockService = {
    getById: vi.fn(),
    runEvaluation: vi.fn(),
    approve: vi.fn(),
    getHistory: vi.fn(),
  };

  beforeEach(async () => {
    vi.clearAllMocks();
    mockService.getHistory.mockReturnValue(of([]));

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

  it('should load recommendation and history on init', () => {
    mockService.getById.mockReturnValue(of(initialRec));
    mockService.getHistory.mockReturnValue(of(mockHistory));

    fixture = TestBed.createComponent(RecommendationDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.recommendation()?.id).toBe(1);
    expect(mockService.getHistory).toHaveBeenCalledWith(1);
    expect(component.history().length).toBe(1);
    expect(component.history()[0].evaluation_sequence).toBe(1);
  });

  it('should run evaluation and refresh history', () => {
    mockService.getById.mockReturnValue(of(initialRec));
    mockService.runEvaluation.mockReturnValue(of(evaluatedRec));
    mockService.getHistory.mockReturnValue(of(mockHistory));

    fixture = TestBed.createComponent(RecommendationDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    component.onRunEvaluation();

    expect(mockService.runEvaluation).toHaveBeenCalledWith(1);
    expect(mockService.getHistory).toHaveBeenCalledWith(1);
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

  it('should correctly detect buyer modifications in history item', () => {
    const itemWithoutMods: EvaluationHistoryItem = {
      ...mockHistory[0],
      buyer_modifications: null,
    };
    const itemWithMods: EvaluationHistoryItem = {
      ...mockHistory[0],
      buyer_modifications: {
        quantity: { previous: 200, updated: 150 },
      },
    };

    fixture = TestBed.createComponent(RecommendationDetailComponent);
    component = fixture.componentInstance;

    expect(component.hasBuyerModifications(itemWithoutMods)).toBe(false);
    expect(component.hasBuyerModifications(itemWithMods)).toBe(true);
  });
});
