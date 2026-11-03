import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { RecommendationService } from '../../core/services/recommendation.service';
import { ProductLookup, SupplierLookup, RecommendationResponse, SplitAllocation } from '../../core/models/recommendation.model';

@Component({
  selector: 'app-recommendation-form',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="form-page">
      <!-- Back Navigation -->
      <div class="nav-back">
        <a [routerLink]="isEditMode() ? ['/recommendations', recommendationId()] : ['/dashboard']" class="back-link">
          &larr; {{ isEditMode() ? 'Back to Recommendation Details' : 'Back to Dashboard' }}
        </a>
      </div>

      <div class="form-card">
        <div class="card-header">
          <div class="header-badge"> 
            {{ isEditMode() ? 'Edit Recommendation #' + recommendationId() : 'New Purchasing Recommendation' }}
          </div>
          <h1 class="card-title">
            {{ isEditMode() ? 'Modify Purchasing Parameters' : 'Create Purchase Recommendation' }}
          </h1>
          <p class="card-subtitle">
            {{ isEditMode()
              ? 'Update the quantity, preferred supplier, or delivery date. Modifying parameters will reset previous AI evaluations.'
              : 'Submit a new purchase recommendation into the workflow for AI evaluation and buyer approval.' }}
          </p>
        </div>

        <!-- Alert messages -->
        <div *ngIf="errorMessage()" class="alert alert-error">
          <span class="alert-icon">⚠️</span>
          <span>{{ errorMessage() }}</span>
        </div>

        <div *ngIf="isEditMode() && existingRecommendation()?.status === 'APPROVED'" class="alert alert-warning">
          <span class="alert-icon">🔒</span>
          <span>This recommendation has already been approved and cannot be edited.</span>
        </div>

        <!-- Loading spinner -->
        <div *ngIf="loadingData()" class="loading-state">
          <div class="spinner"></div>
          <p>Loading catalog options...</p>
        </div>

        <!-- Form -->
        <form *ngIf="!loadingData()" (ngSubmit)="onSubmit()" #recForm="ngForm" class="form-body">
          <!-- Product Selection -->
          <div class="form-group">
            <label for="productId" class="form-label">
              Product <span class="required">*</span>
            </label>
            <select
              id="productId"
              name="productId"
              class="form-control"
              [(ngModel)]="formData.productId"
              (ngModelChange)="onProductChange($event)"
              required
              [disabled]="isEditMode() || isApproved()"
            >
              <option [ngValue]="null" disabled>Select a product...</option>
              <option *ngFor="let prod of products()" [ngValue]="prod.id">
                {{ prod.name }} ({{ prod.sku }})
              </option>
            </select>
            <span *ngIf="isEditMode()" class="field-hint">
              Product cannot be changed on an existing recommendation.
            </span>
          </div>

          <!-- Single Supplier Selection (When split is disabled) -->
          <div *ngIf="!isSplitEnabled()" class="form-group">
            <label for="supplierId" class="form-label">
              Target Supplier
            </label>
            <select
              id="supplierId"
              name="supplierId"
              class="form-control"
              [(ngModel)]="formData.supplierId"
              [disabled]="isApproved()"
            >
              <option [ngValue]="null">-- Auto-evaluate best supplier with AI --</option>
              <option *ngFor="let supp of suppliers()" [ngValue]="supp.id">
                {{ supp.supplier_name }} (ID #{{ supp.id }})<span *ngIf="supp.unit_price"> - \${{ supp.unit_price | number:'1.2-2' }}/unit</span>
              </option>
            </select>
            <span class="field-hint">
              Showing only suppliers registered for the selected product. The engine will verify if this supplier is optimal or suggest an alternative.
            </span>
          </div>

          <!-- Multi-Vendor Split Sourcing Toggle -->
          <div class="split-toggle-card">
            <label class="toggle-checkbox-label">
              <input
                type="checkbox"
                [checked]="isSplitEnabled()"
                (change)="toggleSplit()"
                [disabled]="isApproved()"
              />
              <span class="toggle-title">🔀 Enable Multi-Vendor Split Sourcing (Scenario 2 / Rule 3)</span>
            </label>
            <span class="field-hint">
              Split the required quantity across two qualified suppliers to mitigate capacity caps or lead time delays.
            </span>
          </div>

          <!-- Split Sourcing Vendor Rows (When split is enabled) -->
          <div *ngIf="isSplitEnabled()" class="split-controls-panel">
            <div class="split-controls-header">
              <span class="split-controls-title">Multi-Supplier Allocation Breakdown</span>
              <span class="split-balance-pill" [class.balance-match]="isSplitQuantityMatched()" [class.balance-mismatch]="!isSplitQuantityMatched()">
                Allocated: {{ splitTotalQuantity() }} / {{ formData.quantity || 0 }} units
              </span>
            </div>

            <!-- Primary Supplier Row -->
            <div class="split-row">
              <div class="form-group flex-1">
                <label class="form-label">Primary Vendor <span class="required">*</span></label>
                <select
                  class="form-control"
                  [(ngModel)]="splitData.primarySupplierId"
                  name="primarySupplierId"
                  required
                  [disabled]="isApproved()"
                >
                  <option [ngValue]="null" disabled>Select primary vendor...</option>
                  <option *ngFor="let supp of suppliers()" [ngValue]="supp.id">
                    {{ supp.supplier_name }} (ID #{{ supp.id }})<span *ngIf="supp.unit_price"> - \${{ supp.unit_price | number:'1.2-2' }}/unit</span>
                  </option>
                </select>
              </div>

              <div class="form-group flex-qty">
                <label class="form-label">Units <span class="required">*</span></label>
                <input
                  type="number"
                  class="form-control"
                  [(ngModel)]="splitData.primaryQuantity"
                  name="primaryQuantity"
                  required
                  min="1"
                  placeholder="e.g. 250"
                  [disabled]="isApproved()"
                />
              </div>
            </div>

            <!-- Secondary Supplier Row -->
            <div class="split-row">
              <div class="form-group flex-1">
                <label class="form-label">Secondary Vendor <span class="required">*</span></label>
                <select
                  class="form-control"
                  [(ngModel)]="splitData.secondarySupplierId"
                  name="secondarySupplierId"
                  required
                  [disabled]="isApproved()"
                >
                  <option [ngValue]="null" disabled>Select secondary vendor...</option>
                  <option *ngFor="let supp of suppliers()" [ngValue]="supp.id">
                    {{ supp.supplier_name }} (ID #{{ supp.id }})<span *ngIf="supp.unit_price"> - \${{ supp.unit_price | number:'1.2-2' }}/unit</span>
                  </option>
                </select>
              </div>

              <div class="form-group flex-qty">
                <label class="form-label">Units <span class="required">*</span></label>
                <input
                  type="number"
                  class="form-control"
                  [(ngModel)]="splitData.secondaryQuantity"
                  name="secondaryQuantity"
                  required
                  min="1"
                  placeholder="e.g. 250"
                  [disabled]="isApproved()"
                />
              </div>
            </div>

            <div *ngIf="suppliers().length < 2" class="split-warning-banner">
              ⚠️ This product has only {{ suppliers().length }} supplier registered. Split sourcing requires at least 2 registered suppliers.
            </div>
            <div *ngIf="!isSplitQuantityMatched()" class="split-warning-banner">
              ⚠️ Sum of split units ({{ splitTotalQuantity() }}) must equal recommended quantity ({{ formData.quantity || 0 }}).
            </div>
            <div *ngIf="splitData.primarySupplierId && splitData.secondarySupplierId && splitData.primarySupplierId === splitData.secondarySupplierId" class="split-warning-banner">
              ⚠️ Primary and secondary vendors must be different companies.
            </div>
          </div>

          <!-- Recommended Quantity -->
          <div class="form-group">
            <label for="quantity" class="form-label">
              Recommended Quantity (Units) <span class="required">*</span>
            </label>
            <input
              type="number"
              id="quantity"
              name="quantity"
              class="form-control"
              [(ngModel)]="formData.quantity"
              required
              min="1"
              placeholder="e.g. 150"
              [disabled]="isApproved()"
            />
          </div>

          <!-- Requested Delivery Date -->
          <div class="form-group">
            <label for="deliveryDate" class="form-label">
              Requested Delivery Date <span class="required">*</span>
            </label>
            <input
              type="date"
              id="deliveryDate"
              name="deliveryDate"
              class="form-control"
              [(ngModel)]="formData.deliveryDate"
              required
              [min]="todayDate"
              [disabled]="isApproved()"
            />
          </div>

          <!-- Form Actions -->
          <div class="form-actions">
            <button
              type="submit"
              class="btn btn-primary"
              [disabled]="submitting() || !recForm.valid || (isSplitEnabled() && !isSplitValid()) || isApproved()"
            >
              <span *ngIf="submitting()" class="spinner-sm"></span>
              {{ submitting() ? 'Saving...' : (isEditMode() ? 'Save Changes' : 'Create Recommendation') }}
            </button>
            <a
              [routerLink]="isEditMode() ? ['/recommendations', recommendationId()] : ['/dashboard']"
              class="btn btn-secondary"
            >
              Cancel
            </a>
          </div>
        </form>
      </div>
    </div>
  `,
  styles: [`
    .form-page {
      max-width: 680px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }
    .nav-back {
      margin-bottom: -0.5rem;
    }
    .back-link {
      font-size: 0.9rem;
      font-weight: 500;
      color: #2563eb;
      text-decoration: none;
    }
    .back-link:hover {
      text-decoration: underline;
    }
    .form-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 2rem;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }
    .card-header {
      margin-bottom: 2rem;
      border-bottom: 1px solid #f1f5f9;
      padding-bottom: 1.25rem;
    }
    .header-badge {
      display: inline-block;
      font-size: 0.75rem;
      font-weight: 700;
      color: #2563eb;
      background: #eff6ff;
      border: 1px solid #dbeafe;
      padding: 0.25rem 0.6rem;
      border-radius: 9999px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.5rem;
    }
    .card-title {
      font-size: 1.5rem;
      font-weight: 700;
      color: #0f172a;
      margin: 0;
    }
    .card-subtitle {
      color: #64748b;
      margin-top: 0.35rem;
      font-size: 0.9rem;
      line-height: 1.45;
    }
    .form-body {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }
    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }
    .form-label {
      font-size: 0.85rem;
      font-weight: 600;
      color: #334155;
    }
    .required {
      color: #dc2626;
    }
    .form-control {
      padding: 0.65rem 0.85rem;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      font-size: 0.95rem;
      color: #0f172a;
      background-color: #ffffff;
      transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
    }
    .form-control:focus {
      outline: none;
      border-color: #2563eb;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }
    .form-control:disabled {
      background-color: #f1f5f9;
      color: #94a3b8;
      cursor: not-allowed;
    }
    .field-hint {
      font-size: 0.75rem;
      color: #64748b;
    }

    /* Split Sourcing Form Styles */
    .split-toggle-card {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 0.85rem 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }
    .toggle-checkbox-label {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      cursor: pointer;
    }
    .toggle-title {
      font-weight: 600;
      font-size: 0.9rem;
      color: #1e293b;
    }
    .split-controls-panel {
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      border-radius: 8px;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
    }
    .split-controls-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.5rem;
      padding-bottom: 0.5rem;
      border-bottom: 1px dashed #86efac;
    }
    .split-controls-title {
      font-weight: 700;
      font-size: 0.85rem;
      color: #166534;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    .split-balance-pill {
      font-size: 0.8rem;
      font-weight: 600;
      padding: 0.2rem 0.6rem;
      border-radius: 9999px;
    }
    .balance-match {
      background: #dcfce7;
      color: #15803d;
      border: 1px solid #86efac;
    }
    .balance-mismatch {
      background: #fef2f2;
      color: #b91c1c;
      border: 1px solid #fecaca;
    }
    .split-row {
      display: flex;
      gap: 0.75rem;
      align-items: flex-start;
    }
    .flex-1 {
      flex: 1;
    }
    .flex-qty {
      width: 140px;
    }
    .split-warning-banner {
      font-size: 0.8rem;
      color: #b45309;
      background: #fffbeb;
      border: 1px solid #fde68a;
      padding: 0.4rem 0.6rem;
      border-radius: 4px;
    }
    .form-actions {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-top: 1rem;
      padding-top: 1.25rem;
      border-top: 1px solid #f1f5f9;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      font-weight: 600;
      padding: 0.6rem 1.25rem;
      border-radius: 6px;
      border: 1px solid transparent;
      cursor: pointer;
      font-size: 0.875rem;
      text-decoration: none;
      transition: all 0.15s ease;
    }
    .btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    .btn-primary {
      background-color: #2563eb;
      color: #ffffff;
    }
    .btn-primary:hover:not(:disabled) {
      background-color: #1d4ed8;
    }
    .btn-secondary {
      background-color: #ffffff;
      color: #475569;
      border-color: #cbd5e1;
    }
    .btn-secondary:hover:not(:disabled) {
      background-color: #f8fafc;
      border-color: #94a3b8;
    }
    .alert {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      font-size: 0.875rem;
      margin-bottom: 1.25rem;
    }
    .alert-error {
      background: #fef2f2;
      border: 1px solid #fecaca;
      color: #991b1b;
    }
    .alert-warning {
      background: #fffbeb;
      border: 1px solid #fde68a;
      color: #92400e;
    }
    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2.5rem;
      gap: 0.75rem;
      color: #64748b;
    }
    .spinner {
      width: 28px;
      height: 28px;
      border: 3px solid #e2e8f0;
      border-top-color: #2563eb;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    .spinner-sm {
      width: 14px;
      height: 14px;
      border: 2px solid rgba(255, 255, 255, 0.4);
      border-top-color: #ffffff;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `]
})
export class RecommendationFormComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly recommendationService = inject(RecommendationService);

  readonly isEditMode = signal<boolean>(false);
  readonly recommendationId = signal<number | null>(null);
  readonly existingRecommendation = signal<RecommendationResponse | null>(null);

  readonly products = signal<ProductLookup[]>([]);
  readonly suppliers = signal<SupplierLookup[]>([]);
  readonly loadingData = signal<boolean>(true);
  readonly submitting = signal<boolean>(false);
  readonly errorMessage = signal<string | null>(null);

  readonly isSplitEnabled = signal<boolean>(false);
  splitData = {
    primarySupplierId: null as number | null,
    primaryQuantity: null as number | null,
    secondarySupplierId: null as number | null,
    secondaryQuantity: null as number | null,
  };

  readonly todayDate = new Date().toISOString().split('T')[0];

  formData = {
    productId: null as number | null,
    supplierId: null as number | null,
    quantity: null as number | null,
    deliveryDate: '',
  };

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      this.isEditMode.set(true);
      this.recommendationId.set(Number(idParam));
    }

    this.loadCatalogAndData();
  }

  loadCatalogAndData(): void {
    this.loadingData.set(true);

    this.recommendationService.getProducts().subscribe({
      next: (prods) => {
        this.products.set(prods);

        const recId = this.recommendationId();
        if (recId) {
          this.recommendationService.getById(recId).subscribe({
            next: (rec) => {
              this.existingRecommendation.set(rec);
              this.formData.productId = rec.product_id;
              this.formData.supplierId = rec.supplier_id;
              this.formData.quantity = rec.recommended_quantity;
              this.formData.deliveryDate = rec.requested_delivery_date;

              if (rec.split_allocation) {
                this.isSplitEnabled.set(true);
                this.splitData.primarySupplierId = rec.split_allocation.primary_supplier_id;
                this.splitData.primaryQuantity = rec.split_allocation.primary_quantity;
                this.splitData.secondarySupplierId = rec.split_allocation.secondary_supplier_id;
                this.splitData.secondaryQuantity = rec.split_allocation.secondary_quantity;
              }

              this.loadSuppliersForProduct(rec.product_id);
              this.loadingData.set(false);
            },
            error: (err) => {
              this.loadingData.set(false);
              this.errorMessage.set(err.error?.detail || 'Failed to load recommendation.');
            }
          });
        } else {
          const defaultDate = new Date();
          defaultDate.setDate(defaultDate.getDate() + 7);
          this.formData.deliveryDate = defaultDate.toISOString().split('T')[0];

          if (prods.length > 0) {
            this.formData.productId = prods[0].id;
            this.loadSuppliersForProduct(prods[0].id);
          } else {
            this.suppliers.set([]);
          }
          this.loadingData.set(false);
        }
      },
      error: () => {
        this.loadingData.set(false);
        this.errorMessage.set('Failed to load product catalog.');
      },
    });
  }

  onProductChange(newProductId: number): void {
    this.formData.productId = newProductId;
    this.formData.supplierId = null;
    this.splitData.primarySupplierId = null;
    this.splitData.secondarySupplierId = null;
    if (newProductId) {
      this.loadSuppliersForProduct(newProductId);
    } else {
      this.suppliers.set([]);
    }
  }

  loadSuppliersForProduct(productId: number): void {
    this.recommendationService.getSuppliers(productId).subscribe({
      next: (supps) => {
        this.suppliers.set(supps);
      },
      error: () => this.errorMessage.set('Failed to load suppliers for selected product.'),
    });
  }

  splitTotalQuantity(): number {
    return (this.splitData.primaryQuantity || 0) + (this.splitData.secondaryQuantity || 0);
  }

  isSplitQuantityMatched(): boolean {
    return this.splitTotalQuantity() === (this.formData.quantity || 0);
  }

  isSplitValid(): boolean {
    if (!this.isSplitEnabled()) return true;
    const matched = this.isSplitQuantityMatched();
    const pId = this.splitData.primarySupplierId;
    const sId = this.splitData.secondarySupplierId;
    const pQty = this.splitData.primaryQuantity;
    const sQty = this.splitData.secondaryQuantity;
    return matched && !!pId && !!sId && pId !== sId && (pQty ?? 0) > 0 && (sQty ?? 0) > 0;
  }

  toggleSplit(): void {
    const next = !this.isSplitEnabled();
    this.isSplitEnabled.set(next);
    if (next) {
      const avail = this.suppliers();
      if (avail.length > 0 && !this.splitData.primarySupplierId) {
        this.splitData.primarySupplierId = this.formData.supplierId || avail[0].id;
      }
      if (avail.length > 1 && !this.splitData.secondarySupplierId) {
        const alt = avail.find(s => s.id !== this.splitData.primarySupplierId);
        this.splitData.secondarySupplierId = alt ? alt.id : avail[1].id;
      }
      const half = Math.floor((this.formData.quantity || 0) / 2);
      if (!this.splitData.primaryQuantity) {
        this.splitData.primaryQuantity = half;
      }
      if (!this.splitData.secondaryQuantity) {
        this.splitData.secondaryQuantity = (this.formData.quantity || 0) - (this.splitData.primaryQuantity || half);
      }
    }
  }

  isApproved(): boolean {
    return this.existingRecommendation()?.status === 'APPROVED';
  }

  onSubmit(): void {
    if (!this.formData.productId || !this.formData.quantity || !this.formData.deliveryDate) {
      this.errorMessage.set('Please fill out all required fields.');
      return;
    }

    let split_alloc: SplitAllocation | null = null;
    if (this.isSplitEnabled()) {
      if (!this.isSplitValid()) {
        this.errorMessage.set('Please resolve split sourcing allocation issues before saving.');
        return;
      }
      split_alloc = {
        primary_supplier_id: this.splitData.primarySupplierId!,
        primary_quantity: this.splitData.primaryQuantity!,
        secondary_supplier_id: this.splitData.secondarySupplierId!,
        secondary_quantity: this.splitData.secondaryQuantity!,
      };
    }

    this.submitting.set(true);
    this.errorMessage.set(null);

    const effectiveSupplierId = this.isSplitEnabled()
      ? this.splitData.primarySupplierId
      : this.formData.supplierId;

    if (this.isEditMode() && this.recommendationId()) {
      const updatePayload: any = {
        recommended_quantity: this.formData.quantity,
        supplier_id: effectiveSupplierId,
        requested_delivery_date: this.formData.deliveryDate,
      };
      if (this.isSplitEnabled() && split_alloc) {
        updatePayload.split_allocation = split_alloc;
      } else if (!this.isSplitEnabled() && this.existingRecommendation()?.split_allocation) {
        updatePayload.split_allocation = null;
      }

      this.recommendationService.update(this.recommendationId()!, updatePayload).subscribe({
        next: (updated) => {
          this.submitting.set(false);
          this.router.navigate(['/recommendations', updated.id]);
        },
        error: (err) => {
          this.submitting.set(false);
          this.errorMessage.set(err.error?.detail || err.message || 'Failed to update recommendation.');
        }
      });
    } else {
      const createPayload: any = {
        product_id: this.formData.productId,
        supplier_id: effectiveSupplierId,
        recommended_quantity: this.formData.quantity,
        requested_delivery_date: this.formData.deliveryDate,
      };
      if (split_alloc) {
        createPayload.split_allocation = split_alloc;
      }

      this.recommendationService.create(createPayload).subscribe({
        next: (created) => {
          this.submitting.set(false);
          this.router.navigate(['/recommendations', created.id]);
        },
        error: (err) => {
          this.submitting.set(false);
          this.errorMessage.set(err.error?.detail || err.message || 'Failed to create recommendation.');
        }
      });
    }
  }
}

