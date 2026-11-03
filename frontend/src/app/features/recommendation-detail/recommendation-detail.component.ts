import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { RecommendationService } from '../../core/services/recommendation.service';
import { EvaluationHistoryItem, RecommendationResponse, SplitAllocation } from '../../core/models/recommendation.model';
import { StatusBadgeComponent } from '../../shared/components/status-badge/status-badge.component';

@Component({
  selector: 'app-recommendation-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, StatusBadgeComponent],
  template: `
    <div class="detail-page">
      <!-- Back Navigation -->
      <div class="nav-back">
        <a routerLink="/dashboard" class="back-link">
          &larr; Back to Recommendations
        </a>
      </div>

      <!-- Loading State -->
      <div *ngIf="loading() && !recommendation()" class="state-card loading-state">
        <div class="spinner"></div>
        <p>Loading recommendation details...</p>
      </div>

      <!-- Error State -->
      <div *ngIf="errorMessage()" class="alert alert-error">
        <div class="alert-icon">⚠️</div>
        <div class="alert-body">
          <div class="alert-title">Error</div>
          <div class="alert-text">{{ errorMessage() }}</div>
        </div>
      </div>

      <!-- Success Notification -->
      <div *ngIf="successMessage()" class="alert alert-success">
        <div class="alert-icon">✓</div>
        <div class="alert-body">
          <div class="alert-title">Success</div>
          <div class="alert-text">{{ successMessage() }}</div>
        </div>
      </div>

      <div *ngIf="recommendation()" class="detail-content">
        <!-- Page Header -->
        <div class="header-card">
          <div class="header-main">
            <div class="header-title-row">
              <h1 class="header-title">Recommendation #{{ recommendation()?.id }}</h1>
              <div class="badges-row">
                <app-status-badge [value]="recommendation()?.status" type="status"></app-status-badge>
                <app-status-badge [value]="recommendation()?.agent_decision" type="decision"></app-status-badge>
              </div>
            </div>
            <p class="header-subtitle">
              Requested delivery on <strong>{{ recommendation()?.requested_delivery_date }}</strong>
            </p>
          </div>

          <!-- Actions Bar -->
          <div class="actions-bar">
            <!-- Run Evaluation Button -->
            <button
              class="btn btn-primary"
              (click)="onRunEvaluation()"
              [disabled]="evaluating() || approving()">
              <span *ngIf="evaluating()" class="spinner-sm"></span>
              <svg *ngIf="!evaluating()" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="btn-icon">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
              </svg>
              {{ evaluating() ? 'Running Engine...' : (recommendation()?.agent_decision ? 'Re-run Evaluation' : 'Run AI Evaluation') }}
            </button>

            <!-- Edit Parameters Button -->
            <a
              *ngIf="canApprove()"
              [routerLink]="['/recommendations', recommendation()?.id, 'edit']"
              class="btn btn-secondary"
              title="Edit parameters before approval"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="btn-icon">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
              </svg>
              Edit Parameters
            </a>

            <!-- Approve Button -->
            <button
              class="btn btn-success"
              (click)="onApprove()"
              [disabled]="!canApprove() || approving() || evaluating()"
              [title]="approveButtonTooltip()">
              <span *ngIf="approving()" class="spinner-sm"></span>
              <svg *ngIf="!approving()" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="btn-icon">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              {{ approving() ? 'Approving...' : (recommendation()?.status === 'APPROVED' ? 'Approved' : 'Approve Recommendation') }}
            </button>
          </div>
        </div>

        <div class="grid-layout">
          <!-- Left Column: Original Recommendation Parameters -->
          <div class="panel">
            <div class="panel-header">
              <h3 class="panel-title">Original Purchasing Recommendation</h3>
              <span class="panel-tag">Source Parameters</span>
            </div>
            <div class="panel-body">
              <div class="info-group">
                <label class="info-label">Product</label>
                <div class="info-value">
                  {{ recommendation()?.product_name || ('Product #' + recommendation()?.product_id) }}
                  <span *ngIf="recommendation()?.product_sku" class="panel-tag">{{ recommendation()?.product_sku }}</span>
                </div>
              </div>

              <div class="info-group">
                <label class="info-label">Target Supplier</label>
                <div class="info-value">
                  {{ recommendation()?.supplier_name || ('Supplier #' + recommendation()?.supplier_id) }}
                  <span class="panel-tag">#{{ recommendation()?.supplier_id }}</span>
                </div>
              </div>

              <div class="info-group">
                <label class="info-label">Recommended Quantity</label>
                <div class="info-value highlight-num">{{ recommendation()?.recommended_quantity }} units</div>
              </div>

              <div class="info-group">
                <label class="info-label">Requested Delivery Date</label>
                <div class="info-value">{{ recommendation()?.requested_delivery_date }}</div>
              </div>

              <div class="info-group">
                <label class="info-label">Current Workflow Status</label>
                <div class="info-value">
                  <app-status-badge [value]="recommendation()?.status" type="status"></app-status-badge>
                </div>
              </div>
            </div>
          </div>

          <!-- Right Column: AI Decision Engine Evaluation -->
          <div class="panel">
            <div class="panel-header">
              <h3 class="panel-title">Strategic Purchasing Intelligence</h3>
              <span class="panel-tag engine-tag">Autonomous Analysis</span>
            </div>

            <div class="panel-body">
              <!-- If evaluated -->
              <div *ngIf="recommendation()?.agent_decision; else notEvaluatedYet">
                <!-- Decision Callout Banner -->
                <div [ngClass]="['decision-banner', 'banner-' + recommendation()?.agent_decision?.toLowerCase()]">
                  <div class="decision-icon">
                    <span *ngIf="recommendation()?.agent_decision === 'ACCEPT'">✓</span>
                    <span *ngIf="recommendation()?.agent_decision === 'MODIFY'">✎</span>
                    <span *ngIf="recommendation()?.agent_decision === 'REJECT'">✕</span>
                    <span *ngIf="recommendation()?.agent_decision === 'INVESTIGATE'">!</span>
                  </div>
                  <div class="decision-content">
                    <div class="decision-heading">
                      Decision: <strong>{{ recommendation()?.agent_decision }}</strong>
                    </div>
                    <div class="decision-sub">
                      {{ getDecisionSubtitle(recommendation()?.agent_decision) }}
                    </div>
                  </div>
                </div>

                <!-- Proposed Modifications (Only shown when actual differences exist) -->
                <div *ngIf="hasModifications()" class="comparison-grid" [class.single-card]="!isQuantityModified() || !isSupplierModified()">
                  <div *ngIf="isQuantityModified()" class="comparison-card">
                    <span class="comp-label">Proposed Quantity Adjustment</span>
                    <div class="comp-values">
                      <div class="comp-item">
                        <span class="val-sub">Original Request</span>
                        <span class="val-num">{{ recommendation()?.recommended_quantity }}</span>
                      </div>
                      <div class="comp-arrow">&rarr;</div>
                      <div class="comp-item val-highlight">
                        <span class="val-sub">AI Suggested</span>
                        <span class="val-num">{{ recommendation()?.agent_suggested_quantity ?? '—' }}</span>
                      </div>
                    </div>
                  </div>

                  <div *ngIf="isSupplierModified()" class="comparison-card">
                    <span class="comp-label">Proposed Supplier Alternative</span>
                    <div class="comp-values">
                      <div class="comp-item">
                        <span class="val-sub">Original Request</span>
                        <span class="val-num">
                          {{ recommendation()?.supplier_name || ('Supplier #' + recommendation()?.supplier_id) }}
                        </span>
                      </div>
                      <div class="comp-arrow">&rarr;</div>
                      <div class="comp-item val-highlight">
                        <span class="val-sub">AI Preferred</span>
                        <span class="val-num">
                          {{ recommendation()?.agent_suggested_supplier_name || (recommendation()?.agent_suggested_supplier_id ? ('Supplier #' + recommendation()?.agent_suggested_supplier_id) : '—') }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Multi-Vendor Split Sourcing Allocation Card (Scenario 2 / Rule 3) -->
                <div *ngIf="splitAllocation()" class="split-card">
                  <div class="split-card-header">
                    <div class="split-badge-title">
                      <span class="split-icon">🔀</span>
                      <span>Multi-Vendor Split Sourcing Allocation</span>
                    </div>
                    <div class="split-total-cost">
                      Total Cost: <strong>\${{ splitAllocation()?.total_cost | number:'1.2-2' }}</strong>
                    </div>
                  </div>

                  <div class="split-grid">
                    <!-- Primary Supplier Card -->
                    <div class="vendor-box primary-vendor-box">
                      <div class="vendor-box-header">
                        <span class="vendor-role primary-role">Primary Vendor (Capacity Capped)</span>
                        <span class="vendor-id-pill">#{{ splitAllocation()?.primary_supplier_id }}</span>
                      </div>
                      <div class="vendor-box-name">{{ splitAllocation()?.primary_supplier_name || ('Supplier #' + splitAllocation()?.primary_supplier_id) }}</div>
                      <div class="vendor-box-metrics">
                        <div class="metric-row">
                          <span class="metric-lbl">Allocated Units:</span>
                          <span class="metric-val font-bold">{{ splitAllocation()?.primary_quantity }} units</span>
                        </div>
                        <div *ngIf="splitAllocation()?.primary_unit_price" class="metric-row">
                          <span class="metric-lbl">Unit Price:</span>
                          <span class="metric-val">\${{ splitAllocation()?.primary_unit_price | number:'1.2-2' }}</span>
                        </div>
                        <div class="metric-row cost-row">
                          <span class="metric-lbl">Subtotal:</span>
                          <span class="metric-val cost-val">\${{ splitAllocation()?.primary_cost | number:'1.2-2' }}</span>
                        </div>
                      </div>
                    </div>

                    <div class="split-plus-icon">+</div>

                    <!-- Secondary Supplier Card -->
                    <div class="vendor-box secondary-vendor-box">
                      <div class="vendor-box-header">
                        <span class="vendor-role secondary-role">Secondary Vendor (Overflow Allocation)</span>
                        <span class="vendor-id-pill">#{{ splitAllocation()?.secondary_supplier_id }}</span>
                      </div>
                      <div class="vendor-box-name">{{ splitAllocation()?.secondary_supplier_name || ('Supplier #' + splitAllocation()?.secondary_supplier_id) }}</div>
                      <div class="vendor-box-metrics">
                        <div class="metric-row">
                          <span class="metric-lbl">Allocated Units:</span>
                          <span class="metric-val font-bold">{{ splitAllocation()?.secondary_quantity }} units</span>
                        </div>
                        <div *ngIf="splitAllocation()?.secondary_unit_price" class="metric-row">
                          <span class="metric-lbl">Unit Price:</span>
                          <span class="metric-val">\${{ splitAllocation()?.secondary_unit_price | number:'1.2-2' }}</span>
                        </div>
                        <div class="metric-row cost-row">
                          <span class="metric-lbl">Subtotal:</span>
                          <span class="metric-val cost-val">\${{ splitAllocation()?.secondary_cost | number:'1.2-2' }}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="split-note">
                    Primary vendor capacity reached ({{ splitAllocation()?.primary_quantity }} units max). Balance fulfilled by qualified alternative vendor to complete {{ (splitAllocation()?.primary_quantity ?? 0) + (splitAllocation()?.secondary_quantity ?? 0) }} total units before target delivery date.
                  </div>
                </div>

                <!-- Structured Reasoning -->
                <div class="reasoning-section">
                  <h4 class="reasoning-title">Purchasing Intelligence Briefing</h4>
                  <div class="reasoning-box briefing-box">
                    <div class="briefing-text">{{ recommendation()?.agent_reasoning }}</div>
                  </div>
                </div>

                <!-- Timestamp -->
                <div class="timestamp-row">
                  <span>Evaluated at:</span>
                  <strong>{{ formatTimestamp(recommendation()?.evaluated_at) }}</strong>
                </div>
              </div>

              <!-- Placeholder when not evaluated -->
              <ng-template #notEvaluatedYet>
                <div class="not-evaluated-placeholder">
                  <div class="placeholder-icon">🤖</div>
                  <h4>No AI Evaluation Available</h4>
                  <p>
                    This recommendation has not been evaluated by the deterministic decision engine yet.
                  </p>
                  <button
                    class="btn btn-primary"
                    (click)="onRunEvaluation()"
                    [disabled]="evaluating()">
                    <span *ngIf="evaluating()" class="spinner-sm"></span>
                    {{ evaluating() ? 'Running Engine...' : 'Run AI Evaluation Now' }}
                  </button>
                </div>
              </ng-template>
            </div>
          </div>
        </div>

        <!-- Evaluation History & Buyer Feedback Loop Section -->
        <div class="history-panel">
          <div class="panel-header">
            <div class="history-title-row">
              <h3 class="panel-title">Evaluation History</h3>
              <span class="panel-tag">{{ history().length }} {{ history().length === 1 ? 'Run' : 'Runs' }} Recorded</span>
            </div>
            <button
              class="btn-toggle-history"
              (click)="toggleHistory()"
              type="button"
            >
              {{ showHistory() ? 'Hide History' : 'View History' }}
            </button>
          </div>

          <div *ngIf="showHistory()" class="panel-body">
            <!-- Loading State -->
            <div *ngIf="loadingHistory() && history().length === 0" class="history-empty">
              <div class="spinner-sm"></div>
              <p>Loading evaluation history...</p>
            </div>

            <!-- Empty State -->
            <div *ngIf="!loadingHistory() && history().length === 0" class="history-empty">
              <p class="text-muted">No evaluations recorded yet. Run an AI evaluation to start tracking the decision history.</p>
            </div>

            <!-- History Timeline / List -->
            <div *ngIf="history().length > 0" class="history-timeline">
              <div
                *ngFor="let item of history()"
                class="history-card"
                [class.latest-card]="item.evaluation_sequence === latestSequence()"
              >
                <!-- Card Header -->
                <div class="history-card-header">
                  <div class="history-meta">
                    <span class="history-badge-num">Evaluation #{{ item.evaluation_sequence }}</span>
                    <span *ngIf="item.evaluation_sequence === latestSequence()" class="badge-latest">Latest Evaluation</span>
                    <span class="history-date">{{ formatTimestamp(item.evaluated_at) }}</span>
                  </div>
                  <app-status-badge [value]="item.agent_decision" type="decision"></app-status-badge>
                </div>

                <!-- Buyer Modifications Callout -->
                <div *ngIf="hasBuyerModifications(item)" class="buyer-diff-callout">
                  <div class="diff-header">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="diff-icon">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                    Buyer Changes Since Previous Evaluation:
                  </div>
                  <div class="diff-items">
                    <div *ngIf="item.buyer_modifications?.quantity" class="diff-pill">
                      Quantity: <span class="diff-prev">{{ item.buyer_modifications?.quantity?.previous }}</span> &rarr; <span class="diff-curr">{{ item.buyer_modifications?.quantity?.updated }} units</span>
                    </div>
                    <div *ngIf="item.buyer_modifications?.supplier" class="diff-pill">
                      Supplier: <span class="diff-prev">{{ item.buyer_modifications?.supplier?.previous_name || ('#' + item.buyer_modifications?.supplier?.previous) }}</span> &rarr; <span class="diff-curr">{{ item.buyer_modifications?.supplier?.updated_name || ('#' + item.buyer_modifications?.supplier?.updated) }}</span>
                    </div>
                  </div>
                </div>

                <!-- Evaluated Parameters Snapshot -->
                <div class="history-params-grid">
                  <div class="param-cell">
                    <span class="cell-label">Evaluated Quantity</span>
                    <span class="cell-val">{{ item.evaluated_quantity }} units</span>
                  </div>
                  <div class="param-cell">
                    <span class="cell-label">Evaluated Supplier</span>
                    <span class="cell-val">{{ item.evaluated_supplier_name || (item.evaluated_supplier_id ? 'Supplier #' + item.evaluated_supplier_id : 'None') }}</span>
                  </div>
                  <div class="param-cell">
                    <span class="cell-label">Decision Status</span>
                    <span class="cell-val font-semibold">{{ item.agent_decision }}</span>
                  </div>
                </div>

                <!-- Explanation / Briefing -->
                <div *ngIf="item.explanation" class="history-explanation">
                  <span class="explanation-title">Reasoning / Intelligence Briefing:</span>
                  <div class="explanation-content">{{ item.explanation }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .detail-page {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }
    .nav-back {
      margin-bottom: -0.5rem;
    }
    .back-link {
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      font-size: 0.9rem;
      font-weight: 500;
      color: #2563eb;
      text-decoration: none;
    }
    .back-link:hover {
      text-decoration: underline;
    }

    .header-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
      flex-wrap: wrap;
      gap: 1rem;
    }
    .header-title-row {
      display: flex;
      align-items: center;
      gap: 1rem;
      flex-wrap: wrap;
    }
    .header-title {
      font-size: 1.75rem;
      font-weight: 700;
      color: #0f172a;
      margin: 0;
    }
    .badges-row {
      display: flex;
      gap: 0.5rem;
      align-items: center;
    }
    .header-subtitle {
      color: #64748b;
      margin: 0.35rem 0 0 0;
      font-size: 0.95rem;
    }

    .actions-bar {
      display: flex;
      gap: 0.75rem;
      align-items: center;
    }

    .grid-layout {
      display: grid;
      grid-template-columns: 1fr 1.4fr;
      gap: 1.5rem;
    }
    @media (max-width: 900px) {
      .grid-layout {
        grid-template-columns: 1fr;
      }
    }

    .panel {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
      display: flex;
      flex-direction: column;
    }
    .panel-header {
      padding: 1rem 1.25rem;
      border-bottom: 1px solid #f1f5f9;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .panel-title {
      font-size: 1.05rem;
      font-weight: 600;
      color: #1e293b;
      margin: 0;
    }
    .panel-tag {
      font-size: 0.75rem;
      font-weight: 600;
      background: #f1f5f9;
      color: #475569;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
    }
    .engine-tag {
      background: #eff6ff;
      color: #1d4ed8;
    }
    .panel-body {
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .info-group {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid #f8fafc;
    }
    .info-group:last-child {
      border-bottom: none;
      padding-bottom: 0;
    }
    .info-label {
      font-size: 0.75rem;
      font-weight: 600;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .info-value {
      font-size: 1rem;
      font-weight: 500;
      color: #0f172a;
    }
    .highlight-num {
      font-size: 1.25rem;
      font-weight: 700;
      color: #0f172a;
    }

    /* Decision Callout Banners */
    .decision-banner {
      display: flex;
      align-items: flex-start;
      gap: 1rem;
      padding: 1rem 1.25rem;
      border-radius: 8px;
    }
    .decision-icon {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 1rem;
      flex-shrink: 0;
    }
    .banner-accept {
      background-color: #ecfdf5;
      border: 1px solid #a7f3d0;
      color: #065f46;
    }
    .banner-accept .decision-icon {
      background-color: #10b981;
      color: white;
    }
    .banner-modify {
      background-color: #eff6ff;
      border: 1px solid #bfdbfe;
      color: #1e40af;
    }
    .banner-modify .decision-icon {
      background-color: #3b82f6;
      color: white;
    }
    .banner-reject {
      background-color: #fef2f2;
      border: 1px solid #fecaca;
      color: #991b1b;
    }
    .banner-reject .decision-icon {
      background-color: #ef4444;
      color: white;
    }
    .banner-investigate {
      background-color: #fffbeb;
      border: 1px solid #fde68a;
      color: #92400e;
    }
    .banner-investigate .decision-icon {
      background-color: #f59e0b;
      color: white;
    }
    .decision-heading {
      font-size: 1.05rem;
    }
    .decision-sub {
      font-size: 0.85rem;
      margin-top: 0.2rem;
      opacity: 0.9;
    }

    /* Comparison Grid */
    .comparison-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }
    .comparison-grid.single-card {
      grid-template-columns: 1fr;
    }
    .comparison-card {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 0.85rem 1rem;
    }
    .comp-label {
      font-size: 0.75rem;
      font-weight: 600;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      display: block;
      margin-bottom: 0.5rem;
    }
    .comp-values {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .comp-item {
      display: flex;
      flex-direction: column;
    }
    .val-sub {
      font-size: 0.7rem;
      color: #94a3b8;
    }
    .val-num {
      font-size: 0.95rem;
      font-weight: 600;
      color: #1e293b;
    }
    .comp-arrow {
      color: #94a3b8;
      font-weight: 700;
    }
    .val-highlight .val-num {
      color: #2563eb;
    }

    /* Multi-Vendor Split Card Styles */
    .split-card {
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      border-radius: 8px;
      padding: 1rem 1.15rem;
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
    }
    .split-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.5rem;
      padding-bottom: 0.65rem;
      border-bottom: 1px dashed #86efac;
    }
    .split-badge-title {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-weight: 700;
      font-size: 0.9rem;
      color: #166534;
    }
    .split-total-cost {
      font-size: 0.85rem;
      color: #14532d;
    }
    .split-grid {
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      gap: 0.75rem;
    }
    @media (max-width: 640px) {
      .split-grid {
        grid-template-columns: 1fr;
      }
    }
    .split-plus-icon {
      font-size: 1.25rem;
      font-weight: 700;
      color: #16a34a;
      text-align: center;
    }
    .vendor-box {
      background: #ffffff;
      border: 1px solid #dcfce7;
      border-radius: 6px;
      padding: 0.75rem 0.85rem;
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    .vendor-box-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 0.25rem;
    }
    .vendor-role {
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    .primary-role {
      color: #0369a1;
    }
    .secondary-role {
      color: #b45309;
    }
    .vendor-id-pill {
      font-size: 0.7rem;
      background: #f1f5f9;
      color: #475569;
      padding: 0.1rem 0.35rem;
      border-radius: 4px;
      font-weight: 600;
    }
    .vendor-box-name {
      font-size: 0.9rem;
      font-weight: 600;
      color: #0f172a;
    }
    .vendor-box-metrics {
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
      font-size: 0.8rem;
      color: #475569;
      margin-top: 0.2rem;
    }
    .metric-row {
      display: flex;
      justify-content: space-between;
    }
    .metric-val {
      color: #1e293b;
    }
    .cost-row {
      border-top: 1px solid #f1f5f9;
      padding-top: 0.2rem;
      margin-top: 0.15rem;
    }
    .cost-val {
      font-weight: 700;
      color: #15803d;
    }
    .split-note {
      font-size: 0.75rem;
      color: #15803d;
      background: #f0fdf4;
      padding: 0.4rem 0.5rem;
      border-radius: 4px;
      line-height: 1.4;
    }

    /* Reasoning Section */
    .reasoning-section {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    .reasoning-title {
      font-size: 0.85rem;
      font-weight: 600;
      color: #475569;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin: 0;
    }
    .reasoning-box {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 1.1rem 1.25rem;
    }
    .briefing-text {
      font-size: 0.875rem;
      color: #1e293b;
      white-space: pre-wrap;
      line-height: 1.6;
    }
    .reasoning-point {
      display: flex;
      align-items: flex-start;
      gap: 0.6rem;
    }
    .bullet {
      color: #2563eb;
      font-weight: 700;
      font-size: 1.1rem;
      line-height: 1.2;
    }
    .reasoning-point p {
      margin: 0;
      font-size: 0.875rem;
      color: #334155;
      line-height: 1.45;
    }

    .timestamp-row {
      display: flex;
      justify-content: space-between;
      font-size: 0.8rem;
      color: #64748b;
      padding-top: 0.5rem;
      border-top: 1px solid #f1f5f9;
    }

    /* Placeholder */
    .not-evaluated-placeholder {
      padding: 2.5rem 1rem;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.75rem;
    }
    .placeholder-icon {
      font-size: 2.5rem;
    }
    .not-evaluated-placeholder h4 {
      margin: 0;
      color: #1e293b;
    }
    .not-evaluated-placeholder p {
      margin: 0;
      font-size: 0.875rem;
      color: #64748b;
      max-width: 340px;
    }

    /* Alerts */
    .alert {
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
      padding: 0.85rem 1.25rem;
      border-radius: 8px;
    }
    .alert-icon {
      font-weight: 700;
    }
    .alert-title {
      font-weight: 600;
      font-size: 0.85rem;
    }
    .alert-text {
      font-size: 0.8rem;
    }
    .alert-error {
      background: #fef2f2;
      border: 1px solid #fecaca;
      color: #991b1b;
    }
    .alert-success {
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      color: #166534;
    }

    /* Buttons */
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      font-weight: 600;
      padding: 0.55rem 1.1rem;
      border-radius: 6px;
      border: 1px solid transparent;
      cursor: pointer;
      font-size: 0.875rem;
      transition: all 0.15s ease-in-out;
    }
    .btn:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }
    .btn-primary {
      background-color: #2563eb;
      color: #ffffff;
    }
    .btn-primary:hover:not(:disabled) {
      background-color: #1d4ed8;
    }
    .btn-success {
      background-color: #16a34a;
      color: #ffffff;
    }
    .btn-success:hover:not(:disabled) {
      background-color: #15803d;
    }
    .btn-icon {
      width: 16px;
      height: 16px;
    }
    .spinner-sm {
      width: 14px;
      height: 14px;
      border: 2px solid rgba(255, 255, 255, 0.4);
      border-top-color: #ffffff;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    .spinner {
      width: 32px;
      height: 32px;
      border: 3px solid #e2e8f0;
      border-top-color: #2563eb;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    .state-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 3rem 1.5rem;
      text-align: center;
    }
    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1rem;
      color: #64748b;
    }

    /* Evaluation History Styles */
    .history-panel {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      margin-top: 0.5rem;
    }
    .history-title-row {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .btn-toggle-history {
      background: transparent;
      border: 1px solid #cbd5e1;
      padding: 0.35rem 0.75rem;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 500;
      color: #334155;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .btn-toggle-history:hover {
      background: #f8fafc;
      border-color: #94a3b8;
    }
    .history-empty {
      padding: 2rem;
      text-align: center;
      color: #64748b;
    }
    .history-timeline {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }
    .history-card {
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 1.25rem;
      background: #f8fafc;
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
      transition: border-color 0.15s ease;
    }
    .history-card.latest-card {
      border-color: #3b82f6;
      background: #ffffff;
      box-shadow: 0 0 0 1px #3b82f6;
    }
    .history-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.5rem;
    }
    .history-meta {
      display: flex;
      align-items: center;
      gap: 0.65rem;
      flex-wrap: wrap;
    }
    .history-badge-num {
      font-weight: 700;
      color: #0f172a;
      font-size: 1rem;
    }
    .badge-latest {
      background: #dbeafe;
      color: #1e40af;
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.15rem 0.5rem;
      border-radius: 9999px;
    }
    .history-date {
      color: #64748b;
      font-size: 0.85rem;
    }
    .buyer-diff-callout {
      background: #fefce8;
      border: 1px solid #fef08a;
      border-radius: 6px;
      padding: 0.75rem 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }
    .diff-header {
      font-size: 0.85rem;
      font-weight: 600;
      color: #854d0e;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }
    .diff-icon {
      width: 14px;
      height: 14px;
    }
    .diff-items {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }
    .diff-pill {
      font-size: 0.85rem;
      color: #713f12;
      background: #ffffff;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      border: 1px solid #fef08a;
    }
    .diff-prev {
      text-decoration: line-through;
      color: #94a3b8;
    }
    .diff-curr {
      font-weight: 600;
      color: #15803d;
    }
    .history-params-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 0.75rem;
      background: #ffffff;
      border: 1px solid #f1f5f9;
      padding: 0.75rem;
      border-radius: 6px;
    }
    .param-cell {
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
    }
    .cell-label {
      font-size: 0.75rem;
      color: #64748b;
      text-transform: uppercase;
      font-weight: 600;
    }
    .cell-val {
      font-size: 0.9rem;
      color: #1e293b;
      font-weight: 500;
    }
    .history-explanation {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      background: #ffffff;
      border: 1px solid #f1f5f9;
      border-radius: 6px;
      padding: 0.85rem;
    }
    .explanation-title {
      font-size: 0.8rem;
      font-weight: 600;
      color: #475569;
      text-transform: uppercase;
      letter-spacing: 0.025em;
    }
    .explanation-content {
      font-size: 0.9rem;
      color: #334155;
      line-height: 1.5;
      white-space: pre-line;
    }
  `]
})
export class RecommendationDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly recommendationService = inject(RecommendationService);

  readonly recommendation = signal<RecommendationResponse | null>(null);
  readonly history = signal<EvaluationHistoryItem[]>([]);
  readonly loading = signal<boolean>(false);
  readonly loadingHistory = signal<boolean>(false);
  readonly evaluating = signal<boolean>(false);
  readonly approving = signal<boolean>(false);
  readonly showHistory = signal<boolean>(true);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);

  readonly latestSequence = computed(() => {
    const h = this.history();
    return h.length > 0 ? Math.max(...h.map(i => i.evaluation_sequence)) : 0;
  });

  readonly splitAllocation = computed<SplitAllocation | null>(() => {
    const rec = this.recommendation();
    if (rec?.split_allocation) return rec.split_allocation;

    const h = this.history();
    if (h && h.length > 0) {
      const latest = h[h.length - 1];
      if (latest.calculations && latest.calculations['split_allocation']) {
        return latest.calculations['split_allocation'] as SplitAllocation;
      }
    }
    return null;
  });

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (id) {
      this.loadRecommendation(id);
    } else {
      this.errorMessage.set('Invalid recommendation ID.');
    }
  }

  loadRecommendation(id: number): void {
    this.loading.set(true);
    this.errorMessage.set(null);

    this.recommendationService.getById(id).subscribe({
      next: (data) => {
        this.recommendation.set(data);
        this.loading.set(false);
        this.loadHistory(id);
      },
      error: (err) => {
        this.loading.set(false);
        this.errorMessage.set(err.error?.detail || err.message || 'Failed to load recommendation.');
      }
    });
  }

  loadHistory(id: number): void {
    this.loadingHistory.set(true);
    this.recommendationService.getHistory(id).subscribe({
      next: (items) => {
        this.history.set(items);
        this.loadingHistory.set(false);
      },
      error: (err) => {
        this.loadingHistory.set(false);
        console.error('Failed to load evaluation history:', err);
      }
    });
  }

  hasBuyerModifications(item: EvaluationHistoryItem): boolean {
    return !!(item.buyer_modifications?.quantity || item.buyer_modifications?.supplier);
  }

  toggleHistory(): void {
    this.showHistory.update(v => !v);
  }

  onRunEvaluation(): void {
    const rec = this.recommendation();
    if (!rec) return;

    this.evaluating.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    this.recommendationService.runEvaluation(rec.id).subscribe({
      next: (updated) => {
        this.recommendation.set(updated);
        this.evaluating.set(false);
        this.loadHistory(updated.id);
        this.successMessage.set(
          `AI Evaluation completed: Decision is ${updated.agent_decision}.`
        );
      },
      error: (err) => {
        this.evaluating.set(false);
        this.errorMessage.set(
          err.error?.detail || err.message || 'Evaluation failed to complete.'
        );
      }
    });
  }

  onApprove(): void {
    const rec = this.recommendation();
    if (!rec) return;

    this.approving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    this.recommendationService.approve(rec.id).subscribe({
      next: (updated) => {
        this.recommendation.set(updated);
        this.approving.set(false);
        this.successMessage.set('Recommendation approved successfully!');
      },
      error: (err) => {
        this.approving.set(false);
        this.errorMessage.set(
          err.error?.detail || err.message || 'Approval failed.'
        );
      }
    });
  }

  canApprove(): boolean {
    const rec = this.recommendation();
    return !!rec && rec.status === 'PENDING_APPROVAL';
  }

  approveButtonTooltip(): string {
    const rec = this.recommendation();
    if (!rec) return '';
    if (rec.status === 'APPROVED') return 'This recommendation has already been approved.';
    if (rec.status !== 'PENDING_APPROVAL') return `Cannot approve: Status is ${rec.status}`;
    return 'Approve this recommendation to confirm purchase intent.';
  }

  getDecisionSubtitle(decision: string | null | undefined): string {
    switch (decision) {
      case 'ACCEPT':
        return 'Recommended parameters are optimal. Stockout risk mitigated within budget and capacity.';
      case 'MODIFY':
        return 'Modifications proposed to quantity or supplier to align with demand, budget, or MOQ.';
      case 'REJECT':
        return 'Purchase is unnecessary. Existing stock and open orders fully cover projected demand.';
      case 'INVESTIGATE':
        return 'Stockout or constraint risk detected that requires human buyer investigation.';
      default:
        return 'Evaluation completed.';
    }
  }

  isQuantityModified(): boolean {
    const rec = this.recommendation();
    if (!rec || rec.agent_suggested_quantity === null || rec.agent_suggested_quantity === undefined) return false;
    return rec.agent_suggested_quantity !== rec.recommended_quantity;
  }

  isSupplierModified(): boolean {
    const rec = this.recommendation();
    if (!rec || rec.agent_suggested_supplier_id === null || rec.agent_suggested_supplier_id === undefined) return false;
    return rec.agent_suggested_supplier_id !== rec.supplier_id;
  }

  hasModifications(): boolean {
    return this.isQuantityModified() || this.isSupplierModified();
  }

  formattedReasoning(): string[] {
    const reasoning = this.recommendation()?.agent_reasoning;
    if (!reasoning) return [];
    // Split on double newlines or bullets if present
    return reasoning
      .split(/\n\n+/)
      .map(s => s.trim())
      .filter(s => s.length > 0);
  }

  formatTimestamp(dateStr: string | null | undefined): string {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      return d.toLocaleString();
    } catch {
      return dateStr;
    }
  }
}

