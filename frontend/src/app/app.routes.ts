import { Routes } from '@angular/router';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { RecommendationDetailComponent } from './features/recommendation-detail/recommendation-detail.component';
import { RecommendationFormComponent } from './features/recommendation-form/recommendation-form.component';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'recommendations/new', component: RecommendationFormComponent },
  { path: 'recommendations/:id/edit', component: RecommendationFormComponent },
  { path: 'recommendations/:id', component: RecommendationDetailComponent },
  { path: '**', redirectTo: 'dashboard' },
];
