# Self-Healing ML Pipeline Architecture

## System Overview

The Self-Healing ML Pipeline is an autonomous MLOps system that continuously monitors production ML models, detects data drift, triggers retraining, and performs hot-swap deployments without human intervention.

## Component Architecture

### 1. Guardian MCP Server (`src/guardian_server.py`)

The central orchestration engine exposing 4 core tools via MCP protocol:

#### 1.1 Monitor Tool (Drift Detection)
- **Input**: Production data samples, training baseline, feature names
- **Process**:
  - Per-feature statistical testing
  - Kolmogorov-Smirnov (KS) test: Detects if distributions differ significantly
  - Wasserstein distance: Measures optimal transport cost between distributions
  - Configurable threshold (default: 0.05)
- **Output**: DriftResult with per-feature analysis
- **Decision Gate**: Triggers retraining if drift detected

#### 1.2 Surgeon Tool (Retraining)
- **Input**: New training data, labels, feature names
- **Process**:
  - Split data: 80% train, 20% validation
  - Fit StandardScaler on training subset
  - Train Random Forest (100 trees, depth=15)
  - Validate on held-out set
  - Save model and scaler to staging registry
  - Track metadata (accuracy, timestamp, hyperparameters)
- **Output**: RetrainingResult with metrics and model path
- **Safety**: Isolated to staging registry until approved

#### 1.3 Judge Tool (Model Evaluation)
- **Input**: Test data, labels
- **Process**:
  - Load production model (current)
  - Load staging model (candidate)
  - Evaluate both on test set
  - Calculate metrics: accuracy, precision, recall, F1
  - Compare performance
  - Apply decision threshold (>1% accuracy improvement)
- **Output**: ModelComparison with metrics and deployment recommendation
- **Decision Gate**: Approves or rejects staging model promotion

#### 1.4 Deployer Tool (Hot-Swap)
- **Input**: Approved staging model
- **Process**:
  - Atomic three-step operation:
    1. Backup: production -> backup registry
    2. Promote: staging -> production registry
    3. Update: pointer to new production model
  - Metadata tracking
  - Maintain rollback capability
- **Output**: DeploymentResult with status and paths
- **Safety**: Backup retained for instant rollback

## Data Flow

```
Production    Training
Traffic  -->  Baseline
  |              |
  |              v
  +----------> Monitor Tool
               (Drift Check)
                  |
         ┌────────┴─────────┐
         |                  |
       NO              YES (Drift)
       DRIFT              |
         |                v
         |           Surgeon Tool
         |          (Retrain Model)
         |                |
         |                v
         |           Staging Model
         |                |
         |                v
         |           Judge Tool
         |         (Evaluate & Compare)
         |                |
         |        ┌───────┴─────────┐
         |        |                 |
         |    BETTER           WORSE/SAME
         |        |                 |
         |        v                 |
         |    Deployer Tool     (Hold)
         |   (Hot-Swap Deploy)      |
         |        |                 |
         +────────┼─────────────────+
                  |
                  v
          Production Model
          (Serving Traffic)
```

## Model Registry Structure

```
models/
├── production/
│   ├── production_model.pkl          # Current serving model
│   ├── production_scaler.pkl         # Feature scaler
│   └── production_metadata.json      # Deployment info
├── staging/
│   ├── staging_model.pkl            # Candidate model
│   ├── staging_scaler.pkl           # Feature scaler
│   └── staging_metadata.json        # Validation metrics
└── backup/
    ├── backup_model.pkl             # Previous production
    ├── backup_scaler.pkl            # Feature scaler
    └── backup_metadata.json         # Previous deployment info
```

## Statistical Methods

### Kolmogorov-Smirnov Test
Used for univariate distribution comparison:
```
H0: Production data comes from same distribution as training
H1: Distributions differ

KS statistic = max|F_train(x) - F_prod(x)|
p-value threshold = 0.05

If KS statistic > threshold: Reject H0, drift detected
```

### Wasserstein Distance
Measures transportation cost between distributions:
```
W(P, Q) = inf E[|X - Y|] over all couplings
        = Optimal Transport cost

Higher distance = Greater distributional shift
Threshold = 0.3 (empirically determined)
```

## Training Pipeline

### Data Processing
1. Concatenate old and new data
2. Stratified split: 80/20 train/validation
3. Fit StandardScaler on training subset only
4. Apply scaler to both train and validation

### Model Training
```
Random Forest Configuration:
- Estimators: 100 trees
- Max Depth: 15 (prevents overfitting)
- Min Samples Split: 5
- Jobs: -1 (parallel processing)
- Random State: 42 (reproducibility)
```

### Validation
- Accuracy: Overall correctness
- Precision: Per-class positive predictions
- Recall: Per-class true positives
- F1: Harmonic mean of precision/recall
- Weighted averaging for imbalanced datasets

## Deployment Safety Mechanisms

### Pre-Deployment Checks
1. **Staging Validation**: New model must improve accuracy >1% OR maintain accuracy with better F1
2. **Test Set Comparison**: Evaluated on held-out test data
3. **Metadata Verification**: Training data size, timestamp, hyperparameters logged

### Atomic Swap Operation
```python
Step 1: Backup current production
    production -> backup (read production, write backup)

Step 2: Promote staging
    staging -> production (copy staging to production registry)

Step 3: Update pointers
    All subsequent calls use new production model
```

### Rollback Capability
- Backup model always retained
- Can restore from backup if production fails
- Manual rollback via tool re-invocation
- Metadata tracks all versions

## Configuration Parameters

### Drift Detection
- `ks_threshold`: KS statistic threshold (default: 0.05)
- `wasserstein_threshold`: Wasserstein distance limit (default: 0.3)
- `feature_subset`: Limit drift check to specific features (default: None = all)
- `window_size`: Recent samples to analyze (default: 1000)

### Retraining
- `validation_split`: Train/validation ratio (default: 0.2)
- `random_state`: Reproducibility seed (default: 42)
- `n_estimators`: Random Forest tree count (default: 100)
- `max_depth`: Tree depth limit (default: 15)

### Deployment
- `accuracy_improvement_threshold`: Minimum improvement (default: 0.01 = 1%)
- `backup_retention`: Keep backup for rollback (default: True)

## Error Handling and Logging

### Logging Levels
- **ERROR**: System failures, deployment aborts, data errors
- **INFO**: Drift detection results, retraining completion, deployments
- **DEBUG**: Feature-level drift stats, model metrics

### Error Recovery
```
Tool Execution Failure
    |
    v
Log error with context
    |
    v
Graceful failure response
    |
    v
Staging remains unchanged
    |
    v
Production model unaffected
```

## Performance Characteristics

### Time Complexity
- **Drift Detection**: O(n*m) where n=samples, m=features
- **Retraining**: O(n*m*log(n)) for Random Forest (sklearn optimized)
- **Model Comparison**: O(n*m) for prediction + metric calculation
- **Deployment**: O(1) atomic operation

### Space Complexity
- **Model Storage**: Varies by features and tree count (~1-10MB typical)
- **Scaler Storage**: O(m) for feature statistics
- **Metadata**: ~1KB per model version

### Expected Runtimes (on 10k samples, 5 features)
- Drift detection: 0.5-2 seconds
- Retraining: 30-60 seconds
- Model comparison: 1-3 seconds
- Deployment: <100ms

## Extension Points

### Custom Drift Detection
Replace KS + Wasserstein with:
- Kullback-Leibler divergence
- Population Stability Index (PSI)
- Adversarial validation
- Custom domain-specific metrics

### Alternative ML Frameworks
Swap RandomForest for:
- XGBoost / LightGBM (gradient boosting)
- Neural networks (sklearn MLPClassifier or PyTorch)
- Ensemble methods (voting classifiers)

### Online Learning
Implement incremental learning:
- Partial fit on streaming data
- Windowed retraining
- Continual learning approaches

### A/B Testing
Add shadow deployment:
- Run staging model in parallel
- Compare metrics before full swap
- Gradual traffic migration

### Monitoring Dashboard
Integrate with:
- Prometheus metrics
- Grafana dashboards
- Datadog/New Relic
- Custom logging pipelines

## Security Considerations

### Data Privacy
- Models operate on feature data only
- No raw data storage
- Scalers fit only on training data
- Metadata logged without sensitive info

### Model Protection
- Serialization via joblib (trusted library)
- Backup versions for audit trail
- Version metadata with timestamps
- Change history tracking

### Deployment Safety
- Atomic operations prevent partial states
- Rollback always available
- Manual approval option for production
- Comprehensive logging for compliance

## Integration Points

### With ML Platform
- Model serving endpoint (replace with new production model)
- Feature store (consume training/validation data)
- Data warehouse (log drift detection results)
- ML Ops dashboard (status and metrics)

### With Orchestration
- Kubernetes: Deploy as service, trigger via API
- Airflow/Prefect: Scheduled drift checks
- Apache Spark: Large-scale retraining
- Ray: Distributed hyperparameter tuning

### With Monitoring
- CloudWatch / StackDriver: Cost and performance metrics
- Prometheus: Quantitative monitoring
- Custom webhooks: Alert integrations
- Slack/PagerDuty: On-call notifications

## Why This Architecture Wins

1. **Autonomous**: No human in the loop once deployed
2. **Safe**: Three-tier registry + rollback capability
3. **Stateless**: Each tool invocation is independent
4. **Observable**: Comprehensive logging and metadata
5. **Extensible**: Pluggable components for different ML frameworks
6. **Enterprise-Ready**: Error handling, versioning, audit trails

This represents real MLOps infrastructure used in production systems.
