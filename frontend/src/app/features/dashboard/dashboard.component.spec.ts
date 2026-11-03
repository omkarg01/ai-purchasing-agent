import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { vi } from 'vitest';
import { DashboardComponent } from './dashboard.component';
import { RecommendationService } from '../../core/services/recommendation.service';
import { RecommendationResponse } from '../../core/models/recommendation.model';

describe('DashboardComponent', () => {
  let component: DashboardComponent;
  let fixture: ComponentFixture<DashboardComponent>;

  const mockRecommendations: RecommendationResponse[] = [
    {
      id: 1,
      product_id: 10,
      recommended_quantity: 100,
      supplier_id: 2,
      requested_delivery_date: '2026-11-15',
      status: 'PENDING_APPROVAL',
      agent_decision: 'ACCEPT',
      agent_suggested_quantity: 100,
      agent_suggested_supplier_id: 2,
      agent_reasoning: 'Demand justified.',
      evaluated_at: '2026-11-03T00:00:00Z',
    },
    {
      id: 2,
      product_id: 20,
      recommended_quantity: 50,
      supplier_id: 3,
      requested_delivery_date: '2026-11-20',
      status: 'APPROVED',
      agent_decision: null,
      agent_suggested_quantity: null,
      agent_suggested_supplier_id: null,
      agent_reasoning: null,
      evaluated_at: null,
    },
  ];

  const mockService = {
    list: vi.fn(),
  };

  beforeEach(async () => {
    vi.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [
        provideRouter([]),
        { provide: RecommendationService, useValue: mockService },
      ],
    }).compileComponents();
  });

  it('should create and load recommendations on init', () => {
    mockService.list.mockReturnValue(of(mockRecommendations));

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.recommendations().length).toBe(2);
    expect(component.countPending()).toBe(1);
    expect(component.countApproved()).toBe(1);
    expect(component.countEvaluated()).toBe(1);
  });

  it('should display error message on load failure', () => {
    mockService.list.mockReturnValue(throwError(() => new Error('Server connection error')));

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.errorMessage()).toContain('Server connection error');
    expect(component.loading()).toBe(false);
  });
});
