# Self-Healing ML Pipeline - Deployment Guide

## Production Deployment

### System Requirements

- Python 3.10+
- 2GB+ RAM for model training
- 500MB+ disk for model registry
- Network connectivity (optional, for data sources)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/self-healing-ml-pipeline.git
   cd self-healing-ml-pipeline
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Create required directories**:
   ```bash
   mkdir -p models data logs
   ```

### Initialization

1. **Create `.env` file**:
   ```
   LOG_LEVEL=INFO
   DRIFT_KS_THRESHOLD=0.05
   DRIFT_WASSERSTEIN_THRESHOLD=0.3
   MODEL_VALIDATION_SPLIT=0.2
   RETRAINING_RANDOM_STATE=42
   ```

2. **Initialize model registry with baseline**:
   ```python
   from src.guardian_server import ensure_directories, save_model_and_scaler
   from sklearn.ensemble import RandomForestClassifier
   from sklearn.preprocessing import StandardScaler
   
   ensure_directories()
   
   # Train initial model on your training data
   X_train = load_your_training_data()
   y_train = load_your_training_labels()
   
   scaler = StandardScaler()
   X_scaled = scaler.fit_transform(X_train)
   
   model = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42)
   model.fit(X_scaled, y_train)
   
   # Save as production model
   metadata = {
       "trained_at": datetime.now().isoformat(),
       "samples_used": len(X_train),
       "validation_accuracy": 0.95,
       "feature_names": ["feature_0", "feature_1", ...],
       "model_type": "RandomForest"
   }
   
   save_model_and_scaler(model, scaler, metadata, "production")
   ```

### Running the Server

1. **Start the MCP server**:
   ```bash
   python src/guardian_server.py
   ```

2. **Integration with Claude Desktop** (if using Claude):
   ```json
   {
     "mcpServers": {
       "ml-guardian": {
         "command": "python",
         "args": ["/path/to/src/guardian_server.py"],
         "disabled": false,
         "autoApprove": []
       }
     }
   }
   ```

3. **Integration with VS Code** (`.vscode/mcp.json`):
   ```json
   {
     "mcpServers": {
       "self-healing-ml": {
         "command": "python",
         "args": ["src/guardian_server.py"],
         "transport": "stdio"
       }
     }
   }
   ```

## Operational Monitoring

### Health Checks

Monitor the server logs for:
- Drift detection results
- Retraining completion
- Model comparison outcomes
- Deployment status

### Common Operations

#### Check for Data Drift
```python
drift_result = await client.call_tool(
    "monitor_data_drift",
    {
        "production_data_samples": recent_samples,
        "training_data_baseline": training_data,
        "feature_names": feature_names,
        "drift_threshold": 0.05
    }
)

if drift_result["has_drift"]:
    print(f"Drift detected: {drift_result['summary']}")
```

#### Trigger Manual Retraining
```python
retrain_result = await client.call_tool(
    "trigger_model_retraining",
    {
        "new_training_data": new_data,
        "new_training_labels": new_labels,
        "feature_names": feature_names
    }
)

print(f"Accuracy: {retrain_result['validation_accuracy']:.4f}")
```

#### Compare Models
```python
comparison = await client.call_tool(
    "judge_model_performance",
    {
        "test_data": test_data,
        "test_labels": test_labels
    }
)

if comparison["should_deploy"]:
    print("New model ready for deployment")
```

#### Deploy Updated Model
```python
deployment = await client.call_tool(
    "deploy_model_hot_swap",
    {}
)

if deployment["success"]:
    print("Model deployed to production")
```

## Monitoring Integration

### Prometheus Metrics

Add to your monitoring stack:
```yaml
- job_name: 'ml_guardian'
  static_configs:
    - targets: ['localhost:8000']
  
  relabel_configs:
    - source_labels: [__address__]
      target_label: __param_target
    - source_labels: [__param_target]
      target_label: instance
    - target_label: __address__
      replacement: localhost:9090
```

### CloudWatch Logs

Stream logs to CloudWatch:
```bash
pip install watchtower

# Configure in __init__
import watchtower
handler = watchtower.CloudWatchLogHandler()
logger.addHandler(handler)
```

### Slack Notifications

Add webhook notifications:
```python
import json
from urllib.request import Request, urlopen

def notify_slack(message, deployment_result):
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    
    payload = {
        "text": message,
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Model Deployment*\n{message}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Status*\n{'Success' if deployment_result['success'] else 'Failed'}"},
                    {"type": "mrkdwn", "text": f"*Time*\n{deployment_result['deployment_time']}"}
                ]
            }
        ]
    }
    
    req = Request(slack_webhook, json.dumps(payload).encode())
    urlopen(req)
```

## Troubleshooting

### Issue: Drift Detection Not Working

**Symptom**: Always returns `has_drift: false`

**Solutions**:
1. Verify baseline data is representative
2. Check feature normalization
3. Lower threshold if sensitivity needed
4. Ensure production data is different from baseline

### Issue: Retraining Fails

**Symptom**: RetrainingResult shows `success: false`

**Solutions**:
1. Check data format (list of lists, proper dimensions)
2. Ensure labels match sample count
3. Verify sufficient samples (minimum 100)
4. Check disk space in models/ directory

### Issue: Model Comparison Shows No Improvement

**Symptom**: `should_deploy: false` even after retraining

**Solutions**:
1. Verify test data is representative
2. Check label distribution
3. Increase training samples
4. Adjust hyperparameters
5. Consider different feature engineering

### Issue: Deployment Fails

**Symptom**: DeploymentResult shows `success: false`

**Solutions**:
1. Ensure staging model exists
2. Check disk space
3. Verify write permissions in models/
4. Check for corrupted model files

## Performance Tuning

### For Large Datasets

```python
# Increase estimators for better accuracy
model = RandomForestClassifier(
    n_estimators=200,      # More trees
    max_depth=20,          # Deeper trees
    n_jobs=-1              # Use all cores
)
```

### For Fast Retraining

```python
# Reduce model complexity
model = RandomForestClassifier(
    n_estimators=50,       # Fewer trees
    max_depth=10,          # Shallower trees
    min_samples_split=10   # Fewer splits
)
```

### For Sensitive Drift Detection

```python
# Lower KS threshold for early detection
drift_threshold=0.03  # Was 0.05, more sensitive
```

## Scaling Considerations

### Distributed Retraining

For large datasets, integrate with Spark:
```python
from pyspark.ml import RandomForestClassifier as SparkRF

# Load data as Spark DataFrame
df = spark.read.parquet("s3://bucket/training_data")

# Train distributed model
model = SparkRF(numTrees=100)
spark_model = model.fit(df)

# Convert back to sklearn for serving
```

### Scheduled Monitoring

Use Airflow for periodic checks:
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

dag = DAG(
    'ml_guardian_monitoring',
    default_args={'owner': 'mlops'},
    schedule_interval=timedelta(hours=1)
)

check_drift = PythonOperator(
    task_id='check_drift',
    python_callable=check_data_drift,
    dag=dag
)

retrain_if_needed = PythonOperator(
    task_id='retrain',
    python_callable=trigger_retraining,
    dag=dag
)

check_drift >> retrain_if_needed
```

## Backup and Recovery

### Model Backup Strategy

1. **Daily Backups**:
   ```bash
   # Cron job: backup models daily
   0 2 * * * cp -r /path/to/models /backup/models_$(date +\%Y\%m\%d)
   ```

2. **Version Control**:
   ```bash
   git add models/production_metadata.json
   git commit -m "Production model update - accuracy improvement"
   ```

3. **Rollback Procedure**:
   ```python
   # Restore from backup
   backup_model, backup_scaler, backup_metadata = load_model_and_scaler("backup")
   save_model_and_scaler(backup_model, backup_scaler, backup_metadata, "production")
   ```

## Security Hardening

### API Authentication

If exposing via HTTP:
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials = Depends(security)):
    if credentials.credentials not in authorized_tokens:
        raise HTTPException(status_code=403)
    return credentials.credentials
```

### Model Integrity

Hash models for tamper detection:
```python
import hashlib

def compute_model_hash(model_path):
    with open(model_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

# Store hash with metadata
metadata['model_hash'] = compute_model_hash(model_path)
```

### Data Privacy

Ensure GDPR/privacy compliance:
```python
# Never store raw data
# Only store statistics (mean, std, quantiles)
training_stats = {
    "feature_0_mean": X_train[:, 0].mean(),
    "feature_0_std": X_train[:, 0].std(),
    # ...
}
```

## Compliance and Auditing

### Audit Trail

All operations logged with:
- Timestamp
- User (if authenticated)
- Operation type
- Input parameters (sanitized)
- Output metrics

### Compliance Reports

Generate periodic reports:
```python
def generate_compliance_report(start_date, end_date):
    logs = query_logs(start_date, end_date)
    
    report = {
        "period": f"{start_date} to {end_date}",
        "total_drift_checks": len([l for l in logs if l['type'] == 'drift']),
        "models_deployed": len([l for l in logs if l['type'] == 'deployment']),
        "average_improvement": calculate_avg_improvement(logs),
        "availability": calculate_uptime(logs)
    }
    
    return report
```

## Production Checklist

- [ ] Python 3.10+ installed
- [ ] Dependencies installed from requirements.txt
- [ ] model/ directory created with initial baseline model
- [ ] .env file configured
- [ ] Logs directory created
- [ ] Initial model evaluated and approved
- [ ] Monitoring integrated (Prometheus/CloudWatch)
- [ ] Backup strategy implemented
- [ ] Rollback tested
- [ ] Team trained on operations
- [ ] Documentation updated
- [ ] Performance baseline established
- [ ] Alert thresholds configured
- [ ] Incident response plan ready

## Support

For issues, refer to:
- ARCHITECTURE.md - System design
- README.md - Feature overview
- demo_client.py - Example usage
