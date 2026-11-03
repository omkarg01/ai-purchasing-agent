import { ComponentFixture, TestBed } from '@angular/core/testing';
import { StatusBadgeComponent } from './status-badge.component';

describe('StatusBadgeComponent', () => {
  let component: StatusBadgeComponent;
  let fixture: ComponentFixture<StatusBadgeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StatusBadgeComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(StatusBadgeComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should render correct class for PENDING_APPROVAL status', () => {
    component.value = 'PENDING_APPROVAL';
    component.type = 'status';
    fixture.detectChanges();

    const element = fixture.nativeElement.querySelector('.badge');
    expect(element.classList.contains('badge-pending')).toBe(true);
    expect(element.textContent).toContain('PENDING APPROVAL');
  });

  it('should render correct class for APPROVED status', () => {
    component.value = 'APPROVED';
    component.type = 'status';
    fixture.detectChanges();

    const element = fixture.nativeElement.querySelector('.badge');
    expect(element.classList.contains('badge-approved')).toBe(true);
    expect(element.textContent).toContain('APPROVED');
  });

  it('should render correct class for ACCEPT decision', () => {
    component.value = 'ACCEPT';
    component.type = 'decision';
    fixture.detectChanges();

    const element = fixture.nativeElement.querySelector('.badge');
    expect(element.classList.contains('badge-accept')).toBe(true);
    expect(element.textContent).toContain('ACCEPT');
  });

  it('should render correct class for MODIFY decision', () => {
    component.value = 'MODIFY';
    component.type = 'decision';
    fixture.detectChanges();

    const element = fixture.nativeElement.querySelector('.badge');
    expect(element.classList.contains('badge-modify')).toBe(true);
  });

  it('should render correct class for REJECT decision', () => {
    component.value = 'REJECT';
    component.type = 'decision';
    fixture.detectChanges();

    const element = fixture.nativeElement.querySelector('.badge');
    expect(element.classList.contains('badge-reject')).toBe(true);
  });

  it('should render correct class for INVESTIGATE decision', () => {
    component.value = 'INVESTIGATE';
    component.type = 'decision';
    fixture.detectChanges();

    const element = fixture.nativeElement.querySelector('.badge');
    expect(element.classList.contains('badge-investigate')).toBe(true);
  });

  it('should handle null/empty value gracefully', () => {
    component.value = null;
    component.type = 'decision';
    fixture.detectChanges();

    const element = fixture.nativeElement.querySelector('.badge');
    expect(element.classList.contains('badge-neutral')).toBe(true);
    expect(element.textContent).toContain('NOT EVALUATED');
  });
});
