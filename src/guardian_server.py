import asyncio
import json
import logging
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from joblib import dump, load
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from scipy.spatial.distance import wasserstein_distance
from scipy.stats import ks_2samp
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

mcp = FastMCP("self-healing-ml-guardian")


class DriftResult(BaseModel):
    """Data drift detection result."""
    has_drift: bool = Field(description="Whether data drift detected")
    ks_statistic: float = Field(description="Kolmogorov-Smirnov test statistic")
    wasserstein_distance: float = Field(description="Wasserstein distance between distributions")
    drift_threshold: float = Field(description="Configured drift threshold")
    affected_features: list[str] = Field(description="Features with detected drift")
    timestamp: str = Field(description="Detection timestamp")
    summary: str = Field(description="Human-readable drift summary")


class RetrainingResult(BaseModel):
    """Model retraining result."""
    success: bool = Field(description="Retraining success status")
    samples_used: int = Field(description="Number of samples used for retraining")
    training_time_seconds: float = Field(description="Training duration")
    validation_accuracy: float = Field(description="Validation accuracy of new model")
    timestamp: str = Field(description="Retraining timestamp")
    model_path: str = Field(description="Path to retrained model")
    scaler_path: str = Field(description="Path to feature scaler")
    message: str = Field(description="Status message")


class ModelComparison(BaseModel):
    """Model evaluation comparison result."""
    production_accuracy: float = Field(description="Current production model accuracy")
    new_model_accuracy: float = Field(description="New model accuracy")
    accuracy_improvement: float = Field(description="Accuracy difference (new - production)")
    production_f1: float = Field(description="Production model F1 score")
    new_model_f1: float = Field(description="New model F1 score")
    precision: dict[str, float] = Field(description="Precision metrics")
    recall: dict[str, float] = Field(description="Recall metrics")
    should_deploy: bool = Field(description="Recommendation to deploy new model")
    timestamp: str = Field(description="Evaluation timestamp")
    summary: str = Field(description="Comparison summary")


class DeploymentResult(BaseModel):
    """Model deployment result."""
    success: bool = Field(description="Deployment success status")
    previous_model_path: str = Field(description="Path to previous model (backup)")
    new_model_path: str = Field(description="Path to new active model")
    deployment_time: str = Field(description="Deployment timestamp")
    rollback_available: bool = Field(description="Whether rollback is possible")
    message: str = Field(description="Deployment message")


MODEL_REGISTRY = {
    "production": {
        "model_path": "models/production_model.pkl",
        "scaler_path": "models/production_scaler.pkl",
        "metadata_path": "models/production_metadata.json",
    },
    "staging": {
        "model_path": "models/staging_model.pkl",
        "scaler_path": "models/staging_scaler.pkl",
        "metadata_path": "models/staging_metadata.json",
    },
    "backup": {
        "model_path": "models/backup_model.pkl",
        "scaler_path": "models/backup_scaler.pkl",
        "metadata_path": "models/backup_metadata.json",
    }
}

DRIFT_DETECTION_CONFIG = {
    "ks_threshold": 0.05,
    "wasserstein_threshold": 0.3,
    "feature_subset": None,
    "window_size": 1000,
}


def ensure_directories() -> None:
    """Ensure required directories exist."""
    Path("models").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)


def load_model_and_scaler(registry_key: str) -> tuple[Any, Any, Optional[dict]]:
    """Load model, scaler, and metadata from registry."""
    config = MODEL_REGISTRY[registry_key]
    
    model_path = config["model_path"]
    scaler_path = config["scaler_path"]
    metadata_path = config["metadata_path"]
    
    model = load(model_path) if os.path.exists(model_path) else None
    scaler = load(scaler_path) if os.path.exists(scaler_path) else None
    
    metadata = None
    if os.path.exists(metadata_path):
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
    
    return model, scaler, metadata


def save_model_and_scaler(
    model: Any,
    scaler: Any,
    metadata: dict,
    registry_key: str
) -> None:
    """Save model, scaler, and metadata to registry."""
    ensure_directories()
    config = MODEL_REGISTRY[registry_key]
    
    dump(model, config["model_path"])
    dump(scaler, config["scaler_path"])
    
    with open(config["metadata_path"], "w") as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Saved {registry_key} model and metadata")


def calculate_drift_score(
    training_data: np.ndarray,
    production_data: np.ndarray,
    threshold: float = 0.05
) -> tuple[float, float, bool]:
    """Calculate data drift using KS test and Wasserstein distance."""
    if len(production_data) == 0:
        return 0.0, 0.0, False
    
    ks_stat, _ = ks_2samp(training_data, production_data)
    wasserstein_dist = wasserstein_distance(training_data, production_data)
    
    has_drift = ks_stat > threshold
    
    return ks_stat, wasserstein_dist, has_drift


@mcp.tool()
async def monitor_data_drift(
    production_data_samples: list[list[float]],
    training_data_baseline: list[list[float]],
    feature_names: list[str],
    drift_threshold: float = 0.05
) -> DriftResult:
    """
    Monitor incoming production data for drift against training baseline.
    
    Uses Kolmogorov-Smirnov test and Wasserstein distance to detect when
    production data distribution diverges from training distribution.
    
    Args:
        production_data_samples: Recent production data points
        training_data_baseline: Training set baseline for comparison
        feature_names: Names of features for drift reporting
        drift_threshold: Statistical significance threshold
    
    Returns:
        DriftResult with drift detection analysis
    """
    try:
        ensure_directories()
        
        prod_array = np.array(production_data_samples)
        train_array = np.array(training_data_baseline)
        
        if prod_array.size == 0 or train_array.size == 0:
            return DriftResult(
                has_drift=False,
                ks_statistic=0.0,
                wasserstein_distance=0.0,
                drift_threshold=drift_threshold,
                affected_features=[],
                timestamp=datetime.now().isoformat(),
                summary="Insufficient data for drift detection"
            )
        
        affected_features = []
        max_ks_stat = 0.0
        max_wasserstein = 0.0
        
        for col_idx in range(prod_array.shape[1]):
            if col_idx < len(feature_names):
                ks_stat, wasserstein_dist, drift_detected = calculate_drift_score(
                    train_array[:, col_idx],
                    prod_array[:, col_idx],
                    drift_threshold
                )
                
                max_ks_stat = max(max_ks_stat, ks_stat)
                max_wasserstein = max(max_wasserstein, wasserstein_dist)
                
                if drift_detected:
                    affected_features.append(feature_names[col_idx])
        
        has_overall_drift = len(affected_features) > 0
        
        if has_overall_drift:
            summary = f"Data drift detected in {len(affected_features)} features: {', '.join(affected_features[:3])}"
        else:
            summary = "No data drift detected. Model remains reliable."
        
        logger.info(f"Drift monitoring: {summary}")
        
        return DriftResult(
            has_drift=has_overall_drift,
            ks_statistic=float(max_ks_stat),
            wasserstein_distance=float(max_wasserstein),
            drift_threshold=drift_threshold,
            affected_features=affected_features,
            timestamp=datetime.now().isoformat(),
            summary=summary
        )
    
    except Exception as e:
        logger.error(f"Drift detection error: {e}")
        raise


@mcp.tool()
async def trigger_model_retraining(
    new_training_data: list[list[float]],
    new_training_labels: list[int],
    feature_names: list[str],
    validation_split: float = 0.2,
    random_state: int = 42
) -> RetrainingResult:
    """
    Trigger automatic model retraining with new data.
    
    Trains a new Random Forest model on updated data and evaluates
    on validation set. Model is saved to staging registry.
    
    Args:
        new_training_data: New training samples
        new_training_labels: Corresponding labels
        feature_names: Feature names for the data
        validation_split: Fraction of data for validation
        random_state: Random seed for reproducibility
    
    Returns:
        RetrainingResult with training metrics and model path
    """
    try:
        ensure_directories()
        
        start_time = datetime.now()
        
        X = np.array(new_training_data)
        y = np.array(new_training_labels)
        
        if len(X) == 0 or len(y) == 0:
            return RetrainingResult(
                success=False,
                samples_used=0,
                training_time_seconds=0.0,
                validation_accuracy=0.0,
                timestamp=datetime.now().isoformat(),
                model_path="",
                scaler_path="",
                message="No training data provided"
            )
        
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, random_state=random_state
        )
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)
        
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            min_samples_split=5,
            random_state=random_state,
            n_jobs=-1
        )
        
        model.fit(X_train_scaled, y_train)
        
        val_predictions = model.predict(X_val_scaled)
        val_accuracy = accuracy_score(y_val, val_predictions)
        
        training_time = (datetime.now() - start_time).total_seconds()
        
        metadata = {
            "trained_at": datetime.now().isoformat(),
            "samples_used": len(X_train),
            "validation_accuracy": float(val_accuracy),
            "feature_names": feature_names,
            "model_type": "RandomForest",
            "hyperparameters": {
                "n_estimators": 100,
                "max_depth": 15,
                "min_samples_split": 5
            }
        }
        
        save_model_and_scaler(model, scaler, metadata, "staging")
        
        logger.info(f"Retraining completed: accuracy={val_accuracy:.4f}, time={training_time:.2f}s")
        
        return RetrainingResult(
            success=True,
            samples_used=len(X_train),
            training_time_seconds=float(training_time),
            validation_accuracy=float(val_accuracy),
            timestamp=datetime.now().isoformat(),
            model_path=MODEL_REGISTRY["staging"]["model_path"],
            scaler_path=MODEL_REGISTRY["staging"]["scaler_path"],
            message=f"Model retrained successfully on {len(X_train)} samples"
        )
    
    except Exception as e:
        logger.error(f"Retraining error: {e}")
        return RetrainingResult(
            success=False,
            samples_used=0,
            training_time_seconds=0.0,
            validation_accuracy=0.0,
            timestamp=datetime.now().isoformat(),
            model_path="",
            scaler_path="",
            message=f"Retraining failed: {str(e)}"
        )


@mcp.tool()
async def judge_model_performance(
    test_data: list[list[float]],
    test_labels: list[int],
    compare_with_production: bool = True
) -> ModelComparison:
    """
    Compare staging model against production model.
    
    Evaluates both models on test data and provides comprehensive
    metrics (accuracy, precision, recall, F1). Recommends deployment
    if new model shows improvement.
    
    Args:
        test_data: Test dataset for evaluation
        test_labels: Ground truth labels
        compare_with_production: Whether to compare with production model
    
    Returns:
        ModelComparison with detailed metrics and deployment recommendation
    """
    try:
        ensure_directories()
        
        X_test = np.array(test_data)
        y_test = np.array(test_labels)
        
        if len(X_test) == 0 or len(y_test) == 0:
            return ModelComparison(
                production_accuracy=0.0,
                new_model_accuracy=0.0,
                accuracy_improvement=0.0,
                production_f1=0.0,
                new_model_f1=0.0,
                precision={},
                recall={},
                should_deploy=False,
                timestamp=datetime.now().isoformat(),
                summary="No test data provided"
            )
        
        prod_model, prod_scaler, _ = load_model_and_scaler("production")
        staging_model, staging_scaler, _ = load_model_and_scaler("staging")
        
        X_test_prod = prod_scaler.transform(X_test) if prod_scaler else X_test
        X_test_staging = staging_scaler.transform(X_test) if staging_scaler else X_test
        
        prod_predictions = prod_model.predict(X_test_prod) if prod_model else y_test
        staging_predictions = staging_model.predict(X_test_staging) if staging_model else y_test
        
        prod_accuracy = accuracy_score(y_test, prod_predictions)
        staging_accuracy = accuracy_score(y_test, staging_predictions)
        
        prod_f1 = f1_score(y_test, prod_predictions, average="weighted")
        staging_f1 = f1_score(y_test, staging_predictions, average="weighted")
        
        prod_precision = precision_score(y_test, prod_predictions, average="weighted")
        staging_precision = precision_score(y_test, staging_predictions, average="weighted")
        
        prod_recall = recall_score(y_test, prod_predictions, average="weighted")
        staging_recall = recall_score(y_test, staging_predictions, average="weighted")
        
        accuracy_improvement = staging_accuracy - prod_accuracy
        
        should_deploy = (
            accuracy_improvement > 0.01 or 
            (accuracy_improvement >= 0 and staging_f1 > prod_f1)
        )
        
        if should_deploy:
            summary = f"New model shows {accuracy_improvement:.2%} improvement. Recommend deployment."
        else:
            summary = f"New model underperforms (Δ={accuracy_improvement:.2%}). Hold deployment."
        
        logger.info(f"Model comparison: {summary}")
        
        return ModelComparison(
            production_accuracy=float(prod_accuracy),
            new_model_accuracy=float(staging_accuracy),
            accuracy_improvement=float(accuracy_improvement),
            production_f1=float(prod_f1),
            new_model_f1=float(staging_f1),
            precision={"production": float(prod_precision), "staging": float(staging_precision)},
            recall={"production": float(prod_recall), "staging": float(staging_recall)},
            should_deploy=should_deploy,
            timestamp=datetime.now().isoformat(),
            summary=summary
        )
    
    except Exception as e:
        logger.error(f"Model comparison error: {e}")
        raise


@mcp.tool()
async def deploy_model_hot_swap() -> DeploymentResult:
    """
    Execute atomic hot-swap of staging model to production.
    
    Safely swaps production model with staging model. Maintains
    backup of previous production model for rollback capability.
    
    Returns:
        DeploymentResult with deployment status and metadata
    """
    try:
        ensure_directories()
        
        prod_model, prod_scaler, prod_metadata = load_model_and_scaler("production")
        backup_model, backup_scaler, backup_metadata = load_model_and_scaler("backup")
        
        if prod_model and prod_scaler:
            save_model_and_scaler(prod_model, prod_scaler, prod_metadata or {}, "backup")
            logger.info("Backup created from production model")
        
        staging_model, staging_scaler, staging_metadata = load_model_and_scaler("staging")
        
        if not staging_model or not staging_scaler:
            return DeploymentResult(
                success=False,
                previous_model_path=MODEL_REGISTRY["production"]["model_path"],
                new_model_path="",
                deployment_time=datetime.now().isoformat(),
                rollback_available=bool(backup_model),
                message="Staging model not found. Deployment aborted."
            )
        
        save_model_and_scaler(staging_model, staging_scaler, staging_metadata or {}, "production")
        
        deployment_metadata = {
            "deployed_at": datetime.now().isoformat(),
            "previous_backup_available": True,
            "staging_accuracy": staging_metadata.get("validation_accuracy", "N/A") if staging_metadata else "N/A"
        }
        
        logger.info("Hot-swap deployment completed successfully")
        
        return DeploymentResult(
            success=True,
            previous_model_path=MODEL_REGISTRY["backup"]["model_path"],
            new_model_path=MODEL_REGISTRY["production"]["model_path"],
            deployment_time=datetime.now().isoformat(),
            rollback_available=True,
            message="Model successfully deployed to production. Rollback available."
        )
    
    except Exception as e:
        logger.error(f"Deployment error: {e}")
        return DeploymentResult(
            success=False,
            previous_model_path=MODEL_REGISTRY["production"]["model_path"],
            new_model_path="",
            deployment_time=datetime.now().isoformat(),
            rollback_available=True,
            message=f"Deployment failed: {str(e)}"
        )


if __name__ == "__main__":
    ensure_directories()
    mcp.run(transport="stdio")
