# Self-Healing ML Pipeline - MLOps Best Practices

## Core Principles

### 1. Autonomous but Auditable
- Automate routine tasks (drift detection, retraining, deployment)
- Log every decision with full context
- Manual override capability when needed
- Compliance-ready audit trail

### 2. Safe by Default
- Three-tier registry (production, staging, backup)
- Automated rollback capability
- Validation before promotion
- Atomic operations prevent partial states

### 3. Observable System
- Comprehensive logging at all levels
- Metrics export for monitoring tools
- Clear error messages with context
- Status dashboards showing system health

### 4. Continuous Improvement
- Feedback loop: monitor → retrain → evaluate → deploy
- A/B testing for model changes
- Performance tracking over time
- Cost-benefit analysis of updates

## Data Drift Monitoring

### Understanding Data Drift

Data drift occurs when production data distribution differs from training data:
- **Seasonal patterns**: E.g., holiday shopping behavior
- **Market changes**: E.g., competitor entry affecting demand
- **System changes**: E.g., upstream algorithm changes
- **User behavior shifts**: E.g., new demographic entering platform

### Detection Strategy

1. **Baseline Selection**
   - Use representative training data
   - Account for known variations (time of day, day of week)
   - Update baseline periodically (not too frequently)

2. **Statistical Thresholds**
   - KS test threshold: 0.05 (standard significance level)
   - Wasserstein distance: 0.3 (empirically tuned)
   - Per-feature analysis catches subtle shifts
   - Aggregate analysis identifies overall drift

3. **Monitoring Frequency**
   - Hourly for critical systems
   - Daily for batch systems
   - Adjust based on business requirements
   - More frequent = faster response, more false positives

### Handling False Positives

Drift detected but model still performs well:
```python
# Investigate the drift
# Option 1: Accept drift, performance is stable
# Option 2: Retrain anyway to keep model fresh
# Option 3: Adjust thresholds if too sensitive

# Track false positive rate to optimize thresholds
false_positives = [
    drift for drift in drift_history
    if drift['detected'] and model_performance_stable
]
```

## Model Retraining Best Practices

### Data Preparation

1. **Data Quality**
   - Remove duplicates and errors
   - Handle missing values appropriately
   - Maintain label distribution (avoid skewing)
   - Feature consistency across time periods

2. **Train/Validation Split**
   - Use 80/20 split (80% train, 20% validation)
   - Stratified split for imbalanced classes
   - Time-based split for temporal data
   - Never use test data for training

3. **Feature Scaling**
   - Fit scaler on training data only
   - Apply same scaler to validation and production
   - Prevent data leakage through proper scaling

### Model Selection

```python
# Random Forest is production-ready default because:
# 1. Robust to outliers and non-linear relationships
# 2. Fast inference for serving
# 3. Feature importance tracking
# 4. Handles missing values naturally
# 5. No scaling required for RF

# For different use cases:

# Classification (default)
from sklearn.ensemble import RandomForestClassifier

# High-dimensional data
from sklearn.ensemble import RandomForestClassifier
# Use feature selection to reduce dimensionality

# Imbalanced classes
RandomForestClassifier(class_weight='balanced')

# Large datasets (>100k samples)
# Consider LightGBM or XGBoost for speed
from lightgbm import LGBMClassifier
```

### Validation and Testing

```python
# Comprehensive evaluation
accuracy = accuracy_score(y_test, predictions)
precision = precision_score(y_test, predictions, average='weighted')
recall = recall_score(y_test, predictions, average='weighted')
f1 = f1_score(y_test, predictions, average='weighted')

# Per-class metrics
from sklearn.metrics import classification_report
print(classification_report(y_test, predictions))

# Confusion matrix for error analysis
from sklearn.metrics import confusion_matrix
cm = confusion_matrix(y_test, predictions)
# Analyze what the model gets wrong
```

## Deployment Strategy

### Pre-Deployment Checklist

```
Before deploying a new model:

1. Performance Verification
   [ ] Accuracy improved >1% OR F1 improved with same accuracy
   [ ] No regression on any metric
   [ ] Consistent across multiple test sets

2. Production Readiness
   [ ] Model serializes/deserializes correctly
   [ ] Inference latency acceptable (<50ms for serving)
   [ ] Memory footprint within budget
   [ ] Scaler matches production features

3. Business Validation
   [ ] Metrics aligned with business goals
   [ ] No unexpected behavior discovered
   [ ] Risk assessment complete

4. Operational Readiness
   [ ] Rollback procedure tested
   [ ] Monitoring alerts configured
   [ ] Team aware of deployment
   [ ] Incident response plan ready
```

### Deployment Timing

```python
# Optimal deployment windows:
# 1. Off-peak hours (low traffic)
# 2. When ops team is available
# 3. Not during critical business periods
# 4. After testing window is complete

# Example: Deploy Mon-Fri 2-3pm (lowest traffic)
# Never: Friday evening, weekends, holidays
```

### Canary Deployment

For ultra-safe deployments:
```python
# Phase 1: Shadow deployment (0% traffic)
# - New model runs in parallel
# - Compare metrics without affecting users

# Phase 2: Canary (5% traffic)
# - Serve 5% of requests with new model
# - Monitor metrics, errors, latency
# - If good, increase to 25%

# Phase 3: Gradual rollout (25% → 50% → 100%)
# - Gradual migration of traffic
# - Watch for anomalies at each step
# - Instant rollback if needed

# Phase 4: Full production (100% traffic)
# - All traffic served by new model
# - Keep backup available for quick rollback
```

## Model Monitoring

### Production Metrics

Track these in production:
```python
monitoring_metrics = {
    "inference_latency": [],      # ms per prediction
    "prediction_distribution": [], # How predictions change over time
    "confidence_scores": [],       # Model uncertainty
    "feature_values": [],          # Input distributions
    "error_rate": [],             # Prediction errors (labeled feedback)
}
```

### Alert Thresholds

Set up alerts for:
```python
alerts = {
    "inference_latency_p99": 100,        # Alert if p99 latency > 100ms
    "error_rate_spike": 0.05,            # Alert if error rate increases 5%
    "drift_detected": True,              # Alert on any drift
    "model_staleness": 30,               # Days since last retrain
    "prediction_distribution_shift": 0.1, # Alert on output shift
}
```

### Feedback Loop

```python
# Continuously collect ground truth
# Create labeled dataset of recent predictions

user_feedback = {
    "prediction_id": 12345,
    "predicted_label": 1,
    "true_label": 0,      # User/system corrected label
    "timestamp": "2024-01-15T10:30:00Z",
    "confidence": 0.67
}

# Periodically:
# 1. Check if production model accuracy declining
# 2. Trigger retraining if drift or accuracy loss detected
# 3. Evaluate new model on recent feedback
# 4. Deploy if metrics improve
```

## Cost Optimization

### Model Registry Optimization

```python
# Keep only essential models
models_to_keep = {
    "production": "Current serving model",
    "staging": "Next candidate",
    "backup": "Previous version for rollback",
}

# Archive old models
old_models = [
    m for m in model_history
    if m['deployed_at'] < datetime.now() - timedelta(days=90)
]

for model in old_models:
    archive_to_s3(model)
    delete_local_copy(model)
```

### Retraining Frequency

Balance cost vs performance:
```python
# Option 1: Only on drift detection (event-driven)
# - Lower cost
# - Reactive approach
# - Best for stable data

# Option 2: Daily retraining (scheduled)
# - Higher cost
# - Proactive approach
# - Best for fast-changing data

# Option 3: Hybrid (drift check hourly, retrain weekly)
# - Balanced cost and responsiveness
# - Catches sudden drift
# - Regular baseline refresh
```

### Infrastructure Efficiency

```python
# Use spot instances for retraining
# Spot instances = 70% cheaper than on-demand

# Example with AWS:
# - Production: on-demand (availability critical)
# - Retraining: spot instances (can be interrupted)
# - Staging: spot instances (can be interrupted)

# Estimate: $500/month on-demand → $150/month with spots
```

## Model Governance

### Version Control

```python
# Track all model changes
git log --oneline models/production_metadata.json

# Example output:
# 8c3f2a1 Deployment: accuracy 0.945 (improvement from 0.932)
# 7b2e1f0 Rollback: previous model had latency issues
# 6a1d0e9 Initial production model
```

### Model Card Documentation

Create for each model:
```json
{
  "model_id": "production_v12",
  "trained_at": "2024-01-15T10:30:00Z",
  "training_data": {
    "size": 50000,
    "time_period": "2023-11-01 to 2024-01-15",
    "features": ["age", "income", "credit_score"],
    "target_distribution": {"0": 0.6, "1": 0.4}
  },
  "performance": {
    "accuracy": 0.945,
    "precision": 0.92,
    "recall": 0.96,
    "f1": 0.94
  },
  "limitations": [
    "Performance may degrade for users outside training distribution",
    "Assumes features are available with <1min latency"
  ],
  "ethical_considerations": [
    "Model evaluated for fairness across demographics",
    "No systematic bias detected in test set"
  ],
  "deployment_notes": "Replaced v11 due to data drift in age feature"
}
```

### Fairness and Bias

```python
# Check for demographic parity
def check_fairness(predictions, sensitive_attributes, labels):
    for group in sensitive_attributes.unique():
        group_mask = sensitive_attributes == group
        group_accuracy = accuracy_score(
            labels[group_mask],
            predictions[group_mask]
        )
        print(f"{group}: {group_accuracy:.4f}")
    
    # Flag if any group has <90% of overall accuracy
```

## Incident Response

### When Deployment Goes Wrong

```
Timeline:
T+0: New model deployed
T+5: Alert: error rate increased 15%
T+7: Diagnosis: model predicting wrong for one feature combination
T+10: Decision: Rollback to backup model
T+12: Backup activated, service restored
T+30: Postmortem: feature scaling was missing
T+60: Fix implemented and tested
T+90: Redeployment with fix
```

### Rollback Procedure

```python
# Immediate rollback (< 1 minute)
backup_model, backup_scaler, backup_metadata = load_model_and_scaler("backup")
save_model_and_scaler(backup_model, backup_scaler, backup_metadata, "production")

# All subsequent requests use backup model
# Loss of new features for a few minutes
# Better than serving incorrect predictions
```

### Postmortem Template

```markdown
# Incident: Failed Model Deployment 2024-01-15

**Impact**: 5% increase in error rate for 12 minutes

**Root Cause**: Feature scaler was fitted on full dataset instead of just training split
(Data leakage: test data influenced scaler parameters)

**Why Missed**: Integration test used small synthetic data, didn't catch scaler issue

**Prevention**:
- [ ] Add explicit check: scaler fitted only on training data
- [ ] Require test data >1000 samples
- [ ] Add integration test with real feature distribution

**Action Items**:
- [ ] Fix scaler initialization (done)
- [ ] Update testing procedures (done)
- [ ] Review other models for same issue (in progress)
```

## Team Roles and Responsibilities

### Data Scientists
- Develop and evaluate models
- Investigate model failures
- Tune hyperparameters
- Monitor performance trends

### ML Engineers
- Build infrastructure (this pipeline)
- Manage deployment automation
- Optimize inference latency
- Handle model serving

### Data Engineers
- Ensure data quality
- Manage feature pipeline
- Provide training/test data
- Track data lineage

### Ops / MLOps
- Operate the system
- Configure monitoring/alerts
- Manage infrastructure
- Handle incidents

### Product / Business
- Define success metrics
- Prioritize model improvements
- Monitor business impact
- Report ROI

## Measuring Success

### Technical Metrics
- Model accuracy
- Inference latency (p50, p95, p99)
- Availability (% time model is serving)
- Data drift frequency
- Retraining time

### Business Metrics
- Customer satisfaction
- Revenue impact
- Cost savings
- Time to deploy new model
- Incident response time

### ROI Calculation

```python
# Example: Recommendation system improvement
# Current: 2% conversion rate
# New model: 2.1% conversion rate (5% relative improvement)

annual_users = 1_000_000
conversion_value = 50  # dollars

current_revenue = annual_users * 0.02 * conversion_value  # $1M
new_revenue = annual_users * 0.021 * conversion_value     # $1.05M

improvement = new_revenue - current_revenue               # $50k

development_cost = 40_000  # hours of engineering time
infrastructure_cost = 10_000  # compute, storage, monitoring

roi = (improvement - development_cost - infrastructure_cost) / (development_cost + infrastructure_cost)
# ROI = 0.25 or 25% (1 year payback)
```

## Continuous Learning

### Staying Current
- Follow MLOps conferences (ML4Sys, MLOps.community)
- Monitor research (arXiv papers on drift detection, continual learning)
- Experiment with new techniques in staging
- Share learnings with team

### Build Community
- Open source contributions
- Internal knowledge sharing sessions
- Mentoring junior engineers
- Documentation for future reference

This is production-grade MLOps. Master these practices and you're operating at the level of Netflix, Uber, and other ML-driven companies.
