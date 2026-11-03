import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span [ngClass]="['badge', getBadgeClass()]">
      <span class="dot"></span>
      {{ formatText() }}
    </span>
  `,
  styles: [`
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.25rem 0.625rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      letter-spacing: 0.025em;
      text-transform: uppercase;
      white-space: nowrap;
    }
    .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background-color: currentColor;
    }

    /* Decision styles */
    .badge-accept {
      background-color: #ecfdf5;
      color: #065f46;
      border: 1px solid #a7f3d0;
    }
    .badge-modify {
      background-color: #eff6ff;
      color: #1e40af;
      border: 1px solid #bfdbfe;
    }
    .badge-reject {
      background-color: #fef2f2;
      color: #991b1b;
      border: 1px solid #fecaca;
    }
    .badge-investigate {
      background-color: #fffbeb;
      color: #92400e;
      border: 1px solid #fde68a;
    }

    /* Approval Status styles */
    .badge-pending {
      background-color: #fefce8;
      color: #854d0e;
      border: 1px solid #fef08a;
    }
    .badge-approved {
      background-color: #f0fdf4;
      color: #166534;
      border: 1px solid #bbf7d0;
    }

    /* Neutral */
    .badge-neutral {
      background-color: #f1f5f9;
      color: #475569;
      border: 1px solid #e2e8f0;
    }
  `]
})
export class StatusBadgeComponent {
  @Input() value: string | null | undefined = null;
  @Input() type: 'status' | 'decision' = 'status';

  getBadgeClass(): string {
    if (!this.value) {
      return 'badge-neutral';
    }

    const val = this.value.toUpperCase();

    if (this.type === 'decision') {
      switch (val) {
        case 'ACCEPT':
          return 'badge-accept';
        case 'MODIFY':
          return 'badge-modify';
        case 'REJECT':
          return 'badge-reject';
        case 'INVESTIGATE':
          return 'badge-investigate';
        default:
          return 'badge-neutral';
      }
    } else {
      switch (val) {
        case 'PENDING_APPROVAL':
          return 'badge-pending';
        case 'APPROVED':
          return 'badge-approved';
        case 'REJECTED':
          return 'badge-reject';
        default:
          return 'badge-neutral';
      }
    }
  }

  formatText(): string {
    if (!this.value) {
      return this.type === 'decision' ? 'NOT EVALUATED' : 'UNKNOWN';
    }
    return this.value.replace(/_/g, ' ');
  }
}

