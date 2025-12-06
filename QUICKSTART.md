# Self-Healing ML Pipeline - Quick Start Guide

## 5-Minute Setup

### Step 1: Install Dependencies (1 min)

```bash
pip install -r requirements.txt
```

This installs:
- `mcp` - Model Context Protocol SDK
- `scikit-learn` - ML models and preprocessing
- `numpy`, `scipy`, `pandas` - Data manipulation
- `joblib` - Model serialization
- `python-dotenv` - Configuration management

### Step 2: Create Directories (30 seconds)

```bash
mkdir -p models data logs
```

### Step 3: Start the Server (30 seconds)

```bash
python src/guardian_server.py
```

You should see:
```
INFO:__main__:Guardian MCP Server started
```

### Step 4: Run Demo (3 minutes)

In a new terminal:

```bash
python demo_client.py
```

This demonstrates:
1. Drift detection on normal data (no drift expected)
2. Drift detection on shifted data (drift detected)
3. Model retraining with new data
4. Model comparison (staging vs production)
5. Hot-swap deployment
6. Full end-to-end pipeline

## System Components

### 4 Core Tools

#### 1. monitor_data_drift
Detects when production data distribution changes:
```python
drift_result = await client.call_tool("monitor_data_drift", {
    "production_data_samples": [[1.0, 2.0], [3.0, 4.0]],
    "training_data_baseline": [[0.5, 1.5], [1.5, 2.5]],
    "feature_names": ["feature_a", "feature_b"]
})
# Returns: DriftResult with has_drift, statistics, affected features
```

#### 2. trigger_model_retraining
Trains new model on fresh data:
```python
retrain_result = await client.call_tool("trigger_model_retraining", {
    "new_training_data": [[1.0, 2.0], [3.0, 4.0]],
    "new_training_labels": [0, 1],
    "feature_names": ["feature_a", "feature_b"]
})
# Returns: RetrainingResult with accuracy, samples used, model path
```

#### 3. judge_model_performance
Compares staging vs production model:
```python
comparison = await client.call_tool("judge_model_performance", {
    "test_data": [[2.0, 3.0], [4.0, 5.0]],
    "test_labels": [0, 1]
})
# Returns: ModelComparison with metrics and deployment recommendation
```

#### 4. deploy_model_hot_swap
Safely promotes staging model to production:
```python
deployment = await client.call_tool("deploy_model_hot_swap", {})
# Returns: DeploymentResult with status and rollback info
```

## Complete Workflow

### Autonomous Loop
```
┌─────────────────────────────────┐
│   Monitor Data Drift (hourly)   │
└──────────────┬──────────────────┘
               │
         Drift Detected?
         YES ↓
     ┌─────────────────────────────┐
     │   Trigger Retraining        │
     └──────────────┬──────────────┘
                    │
                    ↓
        ┌──────────────────────────┐
        │  Judge Performance       │
        └──────────────┬───────────┘
                       │
              Better Accuracy?
              YES ↓
         ┌─────────────────────────┐
         │  Hot-Swap Deployment    │
         └─────────────────────────┘
                    │
                    ↓
         Production Updated!
```

## File Structure

```
self-healing-ml-pipeline/
├── src/
│   └── guardian_server.py      # MCP server with 4 tools
├── demo_client.py              # Demo and testing
├── README.md                   # Feature overview
├── ARCHITECTURE.md             # System design details
├── DEPLOYMENT.md               # Production deployment guide
├── MLOPS_BEST_PRACTICES.md    # Industry best practices
├── requirements.txt            # Dependencies
├── pyproject.toml             # Project configuration
├── models/                     # Model registry (auto-created)
├── data/                       # Training data (auto-created)
└── logs/                       # System logs (auto-created)
```

## Configuration

Edit `.env` to customize behavior:

```env
# Logging level
LOG_LEVEL=INFO

# Drift detection thresholds
DRIFT_KS_THRESHOLD=0.05              # Kolmogorov-Smirnov test
DRIFT_WASSERSTEIN_THRESHOLD=0.3     # Wasserstein distance

# Training parameters
MODEL_VALIDATION_SPLIT=0.2           # 80/20 train/validation
RETRAINING_RANDOM_STATE=42           # Reproducibility

# Model hyperparameters
RANDOM_FOREST_ESTIMATORS=100         # Tree count
RANDOM_FOREST_MAX_DEPTH=15           # Tree depth limit
```

## Using with Claude Desktop

To integrate with Claude:

1. Find your Claude config file:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add the MCP server:
   ```json
   {
     "mcpServers": {
       "ml-guardian": {
         "command": "python",
         "args": ["/path/to/self-healing-ml-pipeline/src/guardian_server.py"],
         "disabled": false
       }
     }
   }
   ```

3. Restart Claude

4. Ask Claude: "Monitor for data drift" or "Deploy updated model"

## Common Use Cases

### Case 1: Hourly Drift Monitoring
```python
# Scheduled every hour
drift = await monitor_data_drift(
    production_data_samples=recent_1hour_data,
    training_data_baseline=training_data,
    feature_names=feature_names
)

if drift.has_drift:
    log.warning(f"Drift detected: {drift.summary}")
    # Alert team, trigger manual review if needed
```

### Case 2: Nightly Retraining
```python
# Scheduled nightly
new_data = load_data_since_last_retrain()

retrain = await trigger_model_retraining(
    new_training_data=new_data,
    new_training_labels=new_labels,
    feature_names=feature_names
)

if retrain.success:
    comparison = await judge_model_performance(test_data, test_labels)
    
    if comparison.should_deploy:
        await deploy_model_hot_swap()
```

### Case 3: On-Demand Evaluation
```python
# Manual deployment workflow
drift = await monitor_data_drift(...)

if drift.has_drift:
    # Trigger retraining
    retrain = await trigger_model_retraining(...)
    
    # Compare models
    comparison = await judge_model_performance(...)
    
    # Review before deployment
    if comparison.should_deploy:
        approval = get_human_approval()
        if approval:
            await deploy_model_hot_swap()
```

## Understanding the Output

### Drift Detection Output
```python
DriftResult(
    has_drift=True,                                # Drift detected
    ks_statistic=0.12,                            # How different (0-1)
    wasserstein_distance=0.45,                    # Transport cost
    affected_features=['age', 'income'],          # Which features drifted
    summary="Data drift detected in 2 features"   # Human readable
)
```

### Model Comparison Output
```python
ModelComparison(
    production_accuracy=0.92,        # Current model
    new_model_accuracy=0.95,         # New model
    accuracy_improvement=0.03,       # 3% improvement
    should_deploy=True,              # Safe to deploy
    summary="New model shows 3% improvement"
)
```

### Deployment Output
```python
DeploymentResult(
    success=True,                    # Deployment succeeded
    message="Model deployed to production",
    rollback_available=True,         # Can revert if needed
    deployment_time="2024-01-15T10:30:00Z"
)
```

## Performance Expectations

On a typical laptop (8GB RAM):

| Operation | Time | Notes |
|-----------|------|-------|
| Drift detection | 0.5-2s | 1000 samples × 5 features |
| Model retraining | 30-60s | 5000 samples |
| Model comparison | 1-3s | 1000 test samples |
| Hot-swap deployment | <100ms | Atomic operation |

## Troubleshooting

### Issue: "No module named 'mcp'"
```bash
pip install mcp>=1.0.0
```

### Issue: "models directory permission denied"
```bash
chmod -R 755 models/
```

### Issue: Demo hangs on drift detection
- Ensure server is running in separate terminal
- Check that src/guardian_server.py is in correct path

### Issue: "Model not found" during comparison
- Run retraining first: `trigger_model_retraining`
- Verify `models/staging_model.pkl` exists

## Next Steps

1. **Read ARCHITECTURE.md** - Understand how it works
2. **Review DEPLOYMENT.md** - Production deployment steps
3. **Study MLOPS_BEST_PRACTICES.md** - Industry patterns
4. **Experiment with demo_client.py** - Try different scenarios
5. **Integrate with your data** - Use real production data
6. **Deploy to production** - Follow deployment checklist

## Key Takeaways

- **Autonomous**: Detects drift, retrains, deploys without human intervention
- **Safe**: Three-tier registry + rollback capability
- **Observable**: Comprehensive logging and metrics
- **Scalable**: Extensible to large-scale retraining
- **Professional**: Production-grade MLOps infrastructure

This represents the kind of system deployed at companies like Netflix, Uber, and Airbnb.

## Questions?

Refer to:
- README.md - Feature overview
- ARCHITECTURE.md - System design
- DEPLOYMENT.md - Production guide
- MLOPS_BEST_PRACTICES.md - Best practices
- demo_client.py - Working examples

## License

MIT License - Use freely in personal and commercial projects.
