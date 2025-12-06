# Self-Healing ML Pipeline - MCP Guardian Server

A production-ready autonomous MCP system that monitors deployed ML models, detects data drift, triggers retraining, and automatically hot-swaps models without human intervention.

## Overview

This system addresses a critical problem in ML operations: **stale models**. When user behavior or data distributions change, deployed models degrade. The Self-Healing ML Pipeline continuously monitors production data and autonomously maintains model performance.

## Core Components

### 1. Monitor Tool - Data Drift Detection
Continuously watches production data against training baselines using statistical tests:
- **Kolmogorov-Smirnov (KS) Test**: Detects distribution shifts
- **Wasserstein Distance**: Measures optimal transport distance between distributions
- **Per-Feature Analysis**: Identifies which features caused drift

**Use Case**: Detect when user behavior patterns deviate from training data (e.g., seasonal changes, market shifts, algorithm changes from upstream systems)

### 2. Surgeon Tool - Automatic Retraining
Triggers model retraining when drift is detected:
- Trains new Random Forest model on fresh data
- Uses feature scaling (StandardScaler) for consistency
- Validates on held-out test set
- Saves to staging registry with metadata

**Use Case**: Quickly adapt to new data distributions without manual intervention

### 3. Judge Tool - Model Evaluation
Compares staging model against production model:
- Accuracy, Precision, Recall, F1-Score metrics
- Weighted averaging for imbalanced datasets
- Intelligent deployment recommendation
- >1% accuracy improvement threshold

**Use Case**: Ensure new models don't degrade performance before production deployment

### 4. Deployer Tool - Hot-Swap Deployment
Atomically swaps staging model to production:
- Moves current production model to backup
- Activates staging model as new production
- Maintains rollback capability
- Tracks deployment history

**Use Case**: Zero-downtime model updates in live systems

## Architecture

```
┌─────────────────────┐
│  Production Traffic │
│   & User Behavior   │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────────┐
    │  Monitor Tool    │
    │  (Drift Check)   │
    └────────┬─────────┘
             │
    ┌────────▼─────────┐
    │  Drift Detected? │
    └─┬──────────────┬─┘
      │ NO           │ YES
      │              ▼
      │         ┌─────────────────┐
      │         │ Surgeon Tool    │
      │         │ (Retrain Model) │
      │         └────────┬────────┘
      │                  │
      │                  ▼
      │         ┌─────────────────┐
      │         │  Judge Tool     │
      │         │ (Compare Perf)  │
      │         └────────┬────────┘
      │                  │
      │         ┌────────▼──────────┐
      │         │ Better Model?     │
      │         └┬────────────────┬─┘
      │          │ YES            │ NO
      │          ▼                │
      │      ┌──────────────────┐ │
      │      │  Deployer Tool   │ │
      │      │(Hot-Swap to Prod)│ │
      │      └──────────────────┘ │
      │                           │
      └───────────┬───────────────┘
                  │
                  ▼
         ┌──────────────────┐
         │ Production Model │
         │  (Always Ready)  │
         └──────────────────┘
```

## MLOps Benefits

### Business Value
- **Reduced Stale Model Loss**: Companies lose millions from degraded models. This system maintains performance.
- **Autonomous Operation**: No human intervention needed for routine updates.
- **Risk Mitigation**: Automatic rollback if new model underperforms.

### Technical Advantages
- **Statistical Rigor**: Uses scipy statistical tests for drift detection.
- **Zero-Downtime**: Hot-swap deployment maintains service availability.
- **Explainability**: Per-feature drift tracking identifies what changed.
- **Auditability**: Metadata tracking for all model versions and deployments.

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server**:
   ```bash
   python src/guardian_server.py
   ```

3. **Test with the client**:
   ```bash
   python demo_client.py
   ```

## Usage Example

```python
from src.guardian_server import mcp

# 1. Detect drift
drift_result = await monitor_data_drift(
    production_data_samples=recent_data,
    training_data_baseline=training_data,
    feature_names=feature_names
)

if drift_result.has_drift:
    # 2. Retrain
    retrain_result = await trigger_model_retraining(
        new_training_data=recent_data_with_labels,
        new_training_labels=labels,
        feature_names=feature_names
    )
    
    # 3. Evaluate
    comparison = await judge_model_performance(
        test_data=test_data,
        test_labels=test_labels
    )
    
    # 4. Deploy if better
    if comparison.should_deploy:
        deploy_result = await deploy_model_hot_swap()
```

## Key Features

- **Statistical Drift Detection**: KS test and Wasserstein distance for rigorous analysis
- **Automatic Retraining**: Trains on fresh data without human intervention
- **Model Comparison**: Ensures new models don't degrade performance
- **Zero-Downtime Deployment**: Hot-swap production models safely
- **Version Control**: Maintains backup of previous models for rollback

## System Design Highlights

### Model Registry
Three-tier system for safe deployment:
- **Production**: Currently serving requests
- **Staging**: Candidate for deployment
- **Backup**: Previous production version for rollback

### Drift Detection Algorithm
Statistical tests on feature distributions:
```
For each feature f in production_data:
    ks_stat, p_value = ks_2samp(training_f, production_f)
    wasserstein_dist = wasserstein_distance(training_f, production_f)
    
    if ks_stat > threshold:
        mark_feature_as_drifted()
```

### Model Retraining Pipeline
```
1. Load new training data
2. Split: 80% train, 20% validation
3. Fit StandardScaler on training data
4. Train RandomForest (100 estimators, depth=15)
5. Evaluate on validation set
6. Save to staging registry with metadata
```

### Deployment Safety
```
1. Create backup: production -> backup
2. Promote: staging -> production
3. Maintain rollback capability
4. Track all deployments
```

## Files

- `src/guardian_server.py` - Core MCP server with 4 tools
- `demo_client.py` - Example usage and testing
- `models/` - Model registry (production, staging, backup)
- `data/` - Training and test data storage
- `logs/` - Operational logs

## Why This Wins Recruiter Attention

1. **MLOps Mastery**: Full ML lifecycle understanding
2. **System Architecture**: Autonomous, self-healing system design
3. **Production Ready**: Professional error handling, logging, metadata tracking
4. **Business Impact**: Quantifiable ROI through reduced model decay
5. **Statistical Rigor**: Proper statistical tests for critical decisions
6. **Code Quality**: Type hints, comprehensive docstrings, structured outputs

This is enterprise-grade ML infrastructure, not a kaggle notebook.
