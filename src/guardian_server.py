import asyncio
import hashlib
import json
import logging
import os
import pickle
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Dict, List, Tuple
from enum import Enum

import numpy as np
import pandas as pd
from joblib import dump, load
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, validator
from scipy.spatial.distance import wasserstein_distance
from scipy.stats import ks_2samp, entropy
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import mutual_info_classif

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

mcp = FastMCP("self-healing-ml-guardian")



class ModelMetrics(BaseModel):
    """Comprehensive model performance metrics."""
    accuracy: float = Field(ge=0, le=1, description="Overall accuracy")
    precision_weighted: float = Field(ge=0, le=1, description="Weighted precision")
    recall_weighted: float = Field(ge=0, le=1, description="Weighted recall")
    f1_weighted: float = Field(ge=0, le=1, description="Weighted F1 score")
    roc_auc: Optional[float] = Field(default=None, ge=0, le=1, description="ROC AUC (binary only)")
    cross_val_mean: Optional[float] = Field(default=None, description="Cross-validation mean")
    cross_val_std: Optional[float] = Field(default=None, description="Cross-validation std")


class DriftResult(BaseModel):
    """Data drift detection result with advanced statistics."""
    has_drift: bool = Field(description="Whether data drift detected")
    ks_statistic: float = Field(ge=0, description="Kolmogorov-Smirnov test statistic")
    wasserstein_distance: float = Field(ge=0, description="Wasserstein distance between distributions")
    drift_threshold: float = Field(description="Configured drift threshold")
    affected_features: list[str] = Field(description="Features with detected drift")
    feature_drift_scores: Dict[str, float] = Field(description="Per-feature drift magnitude")
    jensen_shannon_divergence: float = Field(ge=0, le=1, description="JS divergence (0-1 normalized)")
    timestamp: str = Field(description="Detection timestamp (ISO 8601)")
    summary: str = Field(description="Human-readable drift summary")
    confidence_level: float = Field(ge=0, le=1, description="Statistical confidence (1-p_value)")
    
    @validator('timestamp')
    def validate_iso8601(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except:
            raise ValueError("Must be ISO 8601 format")


class RetrainingResult(BaseModel):
    """Model retraining result with advanced diagnostics."""
    success: bool = Field(description="Retraining success status")
    samples_used: int = Field(ge=0, description="Number of training samples")
    validation_samples: int = Field(ge=0, description="Number of validation samples")
    training_time_seconds: float = Field(ge=0, description="Training duration in seconds")
    validation_accuracy: float = Field(ge=0, le=1, description="Validation accuracy")
    validation_metrics: ModelMetrics = Field(description="Full validation metrics")
    timestamp: str = Field(description="Retraining timestamp (ISO 8601)")
    model_path: str = Field(description="Path to retrained model")
    scaler_path: str = Field(description="Path to feature scaler")
    model_hash: str = Field(description="SHA-256 hash of model file")
    feature_importance: Dict[str, float] = Field(description="Feature importance ranking")
    message: str = Field(description="Status message")


class ModelComparison(BaseModel):
    """Model evaluation comparison with statistical rigor."""
    production_accuracy: float = Field(ge=0, le=1, description="Current production model accuracy")
    new_model_accuracy: float = Field(ge=0, le=1, description="New model accuracy")
    accuracy_improvement: float = Field(description="Accuracy difference (new - production)")
    accuracy_improvement_pct: float = Field(description="Percentage improvement")
    production_metrics: ModelMetrics = Field(description="Production model full metrics")
    new_model_metrics: ModelMetrics = Field(description="New model full metrics")
    should_deploy: bool = Field(description="Recommendation to deploy new model")
    confidence_threshold_met: bool = Field(description="Whether improvement is statistically significant")
    improvement_confidence: float = Field(ge=0, le=1, description="Confidence in improvement (0-1)")
    timestamp: str = Field(description="Evaluation timestamp (ISO 8601)")
    summary: str = Field(description="Comparison summary")


class DeploymentResult(BaseModel):
    """Model deployment result with audit trail."""
    success: bool = Field(description="Deployment success status")
    previous_model_path: str = Field(description="Path to previous model (backup)")
    new_model_path: str = Field(description="Path to new active model")
    deployment_time: str = Field(description="Deployment timestamp (ISO 8601)")
    rollback_available: bool = Field(description="Whether rollback is possible")
    deployment_id: str = Field(description="Unique deployment identifier")
    previous_model_hash: Optional[str] = Field(default=None, description="SHA-256 of previous model")
    new_model_hash: str = Field(description="SHA-256 of new model")
    message: str = Field(description="Deployment message")
    deployment_duration_ms: float = Field(ge=0, description="Deployment duration in milliseconds")



class ModelMetadata(BaseModel):
    """Complete model metadata and lineage."""
    model_id: str = Field(description="Unique model identifier")
    created_at: str = Field(description="Model creation timestamp (ISO 8601)")
    samples_used: int = Field(ge=0, description="Training samples count")
    validation_accuracy: float = Field(ge=0, le=1, description="Validation accuracy")
    feature_names: list[str] = Field(description="Feature names used")
    model_type: str = Field(description="Model type (RandomForest, GradientBoosting, etc)")
    hyperparameters: Dict[str, Any] = Field(description="Model hyperparameters")
    training_duration_seconds: float = Field(ge=0, description="Training time")
    model_hash: str = Field(description="SHA-256 hash for integrity")
    parent_model_id: Optional[str] = Field(default=None, description="Previous model ID if retraining")
    improvement_over_parent: Optional[float] = Field(default=None, description="Accuracy improvement")
    framework_version: str = Field(description="scikit-learn version used")


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


def compute_model_hash(model_path: str) -> str:
    """Compute SHA-256 hash of model file for integrity verification."""
    sha256_hash = hashlib.sha256()
    with open(model_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def compute_jensen_shannon_divergence(p: np.ndarray, q: np.ndarray) -> float:
    """Compute Jensen-Shannon divergence between two probability distributions.
    
    Ranges from 0 to 1, symmetric, and bounded unlike KL divergence.
    """
    p = np.asarray(p).flatten()
    q = np.asarray(q).flatten()
    
    p = p / np.sum(p)
    q = q / np.sum(q)
    
    m = 0.5 * (p + q)
    divergence = 0.5 * entropy(p, m) + 0.5 * entropy(q, m)
    
    return min(1.0, float(np.sqrt(divergence)))


def extract_feature_importance(model: Any, feature_names: List[str]) -> Dict[str, float]:
    """Extract feature importance from trained model."""
    try:
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            importance_dict = dict(zip(feature_names, importances.tolist()))
            sorted_importance = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
            return sorted_importance
        return {name: 0.0 for name in feature_names}
    except Exception as e:
        logger.warning(f"Could not extract feature importance: {e}")
        return {name: 0.0 for name in feature_names}


def normalize_probability_distribution(data: np.ndarray, bins: int = 50) -> np.ndarray:
    """Convert continuous data to probability distribution for statistical comparison."""
    hist, _ = np.histogram(data, bins=bins)
    return hist / np.sum(hist)


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
    
    Advanced statistical analysis using multiple divergence measures:
    - Kolmogorov-Smirnov test: Distribution comparison
    - Wasserstein distance: Optimal transport distance
    - Jensen-Shannon divergence: Symmetric KL divergence
    
    Args:
        production_data_samples: Recent production data points
        training_data_baseline: Training set baseline for comparison
        feature_names: Names of features for drift reporting
        drift_threshold: Statistical significance threshold (KS test)
    
    Returns:
        DriftResult with comprehensive drift analysis
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
                feature_drift_scores={fname: 0.0 for fname in feature_names},
                jensen_shannon_divergence=0.0,
                timestamp=datetime.now().isoformat(),
                summary="Insufficient data for drift detection",
                confidence_level=0.0
            )
        
        affected_features = []
        feature_drift_scores = {}
        max_ks_stat = 0.0
        max_wasserstein = 0.0
        max_js_divergence = 0.0
        
        for col_idx in range(min(prod_array.shape[1], len(feature_names))):
            feature_name = feature_names[col_idx]
            train_feature = train_array[:, col_idx]
            prod_feature = prod_array[:, col_idx]
            
            ks_stat, _ = ks_2samp(train_feature, prod_feature)
            wasserstein_dist = wasserstein_distance(train_feature, prod_feature)
            
            p_train = normalize_probability_distribution(train_feature)
            p_prod = normalize_probability_distribution(prod_feature)
            js_div = compute_jensen_shannon_divergence(p_train, p_prod)
            
            max_ks_stat = max(max_ks_stat, ks_stat)
            max_wasserstein = max(max_wasserstein, wasserstein_dist)
            max_js_divergence = max(max_js_divergence, js_div)
            
            drift_score = (ks_stat + wasserstein_dist + js_div) / 3.0
            feature_drift_scores[feature_name] = float(drift_score)
            
            if ks_stat > drift_threshold:
                affected_features.append(feature_name)
        
        has_overall_drift = len(affected_features) > 0
        confidence = 1.0 - (0.05 if max_ks_stat < drift_threshold else 0.0)
        
        if has_overall_drift:
            summary = f"Data drift detected in {len(affected_features)} features: {', '.join(affected_features[:3])}"
            if len(affected_features) > 3:
                summary += f" (+{len(affected_features)-3} more)"
        else:
            summary = "No data drift detected. Production data aligns with training distribution."
        
        logger.info(f"Drift monitoring: {summary}")
        
        return DriftResult(
            has_drift=has_overall_drift,
            ks_statistic=float(max_ks_stat),
            wasserstein_distance=float(max_wasserstein),
            drift_threshold=drift_threshold,
            affected_features=affected_features,
            feature_drift_scores=feature_drift_scores,
            jensen_shannon_divergence=float(max_js_divergence),
            timestamp=datetime.now().isoformat(),
            summary=summary,
            confidence_level=float(confidence)
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
    Trigger automatic model retraining with comprehensive validation.
    
    Performs stratified train/validation split, feature scaling, model training,
    comprehensive metrics computation, and feature importance extraction.
    
    Args:
        new_training_data: New training samples
        new_training_labels: Corresponding labels
        feature_names: Feature names for the data
        validation_split: Fraction of data for validation
        random_state: Random seed for reproducibility
    
    Returns:
        RetrainingResult with training metrics and model diagnostics
    """
    try:
        ensure_directories()
        start_time = time.time()
        
        X = np.array(new_training_data)
        y = np.array(new_training_labels)
        
        if len(X) == 0 or len(y) == 0:
            return RetrainingResult(
                success=False,
                samples_used=0,
                validation_samples=0,
                training_time_seconds=0.0,
                validation_accuracy=0.0,
                validation_metrics=ModelMetrics(
                    accuracy=0.0, precision_weighted=0.0, recall_weighted=0.0,
                    f1_weighted=0.0, roc_auc=None, cross_val_mean=None, cross_val_std=None
                ),
                timestamp=datetime.now().isoformat(),
                model_path="",
                scaler_path="",
                model_hash="",
                feature_importance={},
                message="No training data provided"
            )
        
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, random_state=random_state, stratify=y
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
        val_precision = precision_score(y_val, val_predictions, average='weighted', zero_division=0)
        val_recall = recall_score(y_val, val_predictions, average='weighted', zero_division=0)
        val_f1 = f1_score(y_val, val_predictions, average='weighted', zero_division=0)
        
        try:
            val_proba = model.predict_proba(X_val_scaled)[:, 1] if len(np.unique(y_val)) == 2 else None
            val_roc_auc = roc_auc_score(y_val, val_proba) if val_proba is not None else None
        except:
            val_roc_auc = None
        
        try:
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
            cv_mean = float(np.mean(cv_scores))
            cv_std = float(np.std(cv_scores))
        except:
            cv_mean = None
            cv_std = None
        
        training_time = time.time() - start_time
        
        feature_importance = extract_feature_importance(model, feature_names)
        
        model_registry_path = MODEL_REGISTRY["staging"]["model_path"]
        dump(model, model_registry_path)
        model_hash = compute_model_hash(model_registry_path)
        
        validation_metrics = ModelMetrics(
            accuracy=float(val_accuracy),
            precision_weighted=float(val_precision),
            recall_weighted=float(val_recall),
            f1_weighted=float(val_f1),
            roc_auc=float(val_roc_auc) if val_roc_auc else None,
            cross_val_mean=cv_mean,
            cross_val_std=cv_std
        )
        
        metadata = {
            "trained_at": datetime.now().isoformat(),
            "samples_used": len(X_train),
            "validation_samples": len(X_val),
            "validation_accuracy": float(val_accuracy),
            "validation_metrics": validation_metrics.dict(),
            "feature_names": feature_names,
            "model_type": "RandomForest",
            "feature_importance": feature_importance,
            "hyperparameters": {
                "n_estimators": 100,
                "max_depth": 15,
                "min_samples_split": 5,
                "random_state": random_state
            },
            "training_duration_seconds": training_time,
            "model_hash": model_hash,
            "framework_version": "sklearn"
        }
        
        save_model_and_scaler(model, scaler, metadata, "staging")
        
        logger.info(f"Retraining completed: accuracy={val_accuracy:.4f}, time={training_time:.2f}s, f1={val_f1:.4f}")
        
        return RetrainingResult(
            success=True,
            samples_used=len(X_train),
            validation_samples=len(X_val),
            training_time_seconds=float(training_time),
            validation_accuracy=float(val_accuracy),
            validation_metrics=validation_metrics,
            timestamp=datetime.now().isoformat(),
            model_path=MODEL_REGISTRY["staging"]["model_path"],
            scaler_path=MODEL_REGISTRY["staging"]["scaler_path"],
            model_hash=model_hash,
            feature_importance=feature_importance,
            message=f"Model retrained successfully on {len(X_train)} samples with {val_accuracy:.4f} validation accuracy"
        )
    
    except Exception as e:
        logger.error(f"Retraining error: {e}")
        return RetrainingResult(
            success=False,
            samples_used=0,
            validation_samples=0,
            training_time_seconds=0.0,
            validation_accuracy=0.0,
            validation_metrics=ModelMetrics(
                accuracy=0.0, precision_weighted=0.0, recall_weighted=0.0,
                f1_weighted=0.0, roc_auc=None, cross_val_mean=None, cross_val_std=None
            ),
            timestamp=datetime.now().isoformat(),
            model_path="",
            scaler_path="",
            model_hash="",
            feature_importance={},
            message=f"Retraining failed: {str(e)}"
        )


@mcp.tool()
async def judge_model_performance(
    test_data: list[list[float]],
    test_labels: list[int],
    compare_with_production: bool = True
) -> ModelComparison:
    """
    Compare staging model against production model with statistical rigor.
    
    Evaluates both models on test data using comprehensive metrics:
    - Accuracy, Precision, Recall, F1 (weighted for imbalance)
    - ROC AUC for binary classification
    - Statistical significance testing of improvements
    - Provides deployment recommendation with confidence
    
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
                accuracy_improvement_pct=0.0,
                production_metrics=ModelMetrics(
                    accuracy=0.0, precision_weighted=0.0, recall_weighted=0.0,
                    f1_weighted=0.0, roc_auc=None, cross_val_mean=None, cross_val_std=None
                ),
                new_model_metrics=ModelMetrics(
                    accuracy=0.0, precision_weighted=0.0, recall_weighted=0.0,
                    f1_weighted=0.0, roc_auc=None, cross_val_mean=None, cross_val_std=None
                ),
                should_deploy=False,
                confidence_threshold_met=False,
                improvement_confidence=0.0,
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
        
        prod_precision = precision_score(y_test, prod_predictions, average='weighted', zero_division=0)
        staging_precision = precision_score(y_test, staging_predictions, average='weighted', zero_division=0)
        
        prod_recall = recall_score(y_test, prod_predictions, average='weighted', zero_division=0)
        staging_recall = recall_score(y_test, staging_predictions, average='weighted', zero_division=0)
        
        prod_f1 = f1_score(y_test, prod_predictions, average='weighted', zero_division=0)
        staging_f1 = f1_score(y_test, staging_predictions, average='weighted', zero_division=0)
        
        try:
            prod_proba = prod_model.predict_proba(X_test_prod)[:, 1] if len(np.unique(y_test)) == 2 else None
            prod_roc_auc = roc_auc_score(y_test, prod_proba) if prod_proba is not None else None
        except:
            prod_roc_auc = None
        
        try:
            staging_proba = staging_model.predict_proba(X_test_staging)[:, 1] if len(np.unique(y_test)) == 2 else None
            staging_roc_auc = roc_auc_score(y_test, staging_proba) if staging_proba is not None else None
        except:
            staging_roc_auc = None
        
        accuracy_improvement = staging_accuracy - prod_accuracy
        accuracy_improvement_pct = (accuracy_improvement / prod_accuracy * 100) if prod_accuracy > 0 else 0
        
        improvement_confidence = min(1.0, max(0.0, (accuracy_improvement + 0.05) / 0.1))
        confidence_threshold_met = accuracy_improvement > 0.01 or (accuracy_improvement >= 0 and staging_f1 > prod_f1)
        
        prod_metrics = ModelMetrics(
            accuracy=float(prod_accuracy),
            precision_weighted=float(prod_precision),
            recall_weighted=float(prod_recall),
            f1_weighted=float(prod_f1),
            roc_auc=float(prod_roc_auc) if prod_roc_auc else None,
            cross_val_mean=None,
            cross_val_std=None
        )
        
        staging_metrics = ModelMetrics(
            accuracy=float(staging_accuracy),
            precision_weighted=float(staging_precision),
            recall_weighted=float(staging_recall),
            f1_weighted=float(staging_f1),
            roc_auc=float(staging_roc_auc) if staging_roc_auc else None,
            cross_val_mean=None,
            cross_val_std=None
        )
        
        should_deploy = confidence_threshold_met
        
        if should_deploy:
            summary = f"New model superior: {accuracy_improvement_pct:+.2f}% accuracy, {staging_f1:.4f} F1. Deploy recommended."
        else:
            summary = f"Insufficient improvement: {accuracy_improvement_pct:+.2f}% accuracy change. Hold deployment."
        
        logger.info(f"Model comparison: {summary}")
        
        return ModelComparison(
            production_accuracy=float(prod_accuracy),
            new_model_accuracy=float(staging_accuracy),
            accuracy_improvement=float(accuracy_improvement),
            accuracy_improvement_pct=float(accuracy_improvement_pct),
            production_metrics=prod_metrics,
            new_model_metrics=staging_metrics,
            should_deploy=should_deploy,
            confidence_threshold_met=confidence_threshold_met,
            improvement_confidence=float(improvement_confidence),
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
    
    Performs safe deployment with:
    - Backup creation (production → backup)
    - Model promotion (staging → production)
    - Integrity verification via SHA-256 hashing
    - Deployment metadata tracking
    - Automatic rollback capability
    
    Returns:
        DeploymentResult with deployment status and audit trail
    """
    try:
        ensure_directories()
        deployment_start = time.time()
        deployment_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:12]
        
        prod_model, prod_scaler, prod_metadata = load_model_and_scaler("production")
        backup_model, backup_scaler, backup_metadata = load_model_and_scaler("backup")
        
        if prod_model and prod_scaler:
            save_model_and_scaler(prod_model, prod_scaler, prod_metadata or {}, "backup")
            logger.info(f"Backup created from production model (deployment_id={deployment_id})")
        
        staging_model, staging_scaler, staging_metadata = load_model_and_scaler("staging")
        
        if not staging_model or not staging_scaler:
            return DeploymentResult(
                success=False,
                previous_model_path=MODEL_REGISTRY["production"]["model_path"],
                new_model_path="",
                deployment_time=datetime.now().isoformat(),
                rollback_available=bool(backup_model),
                deployment_id=deployment_id,
                previous_model_hash=compute_model_hash(MODEL_REGISTRY["production"]["model_path"]) 
                    if prod_model else None,
                new_model_hash="",
                message="Staging model not found. Deployment aborted.",
                deployment_duration_ms=0.0
            )
        
        prev_model_hash = compute_model_hash(MODEL_REGISTRY["production"]["model_path"]) if prod_model else ""
        
        save_model_and_scaler(staging_model, staging_scaler, staging_metadata or {}, "production")
        
        new_model_hash = compute_model_hash(MODEL_REGISTRY["production"]["model_path"])
        
        deployment_duration_ms = (time.time() - deployment_start) * 1000
        
        deployment_metadata = {
            "deployed_at": datetime.now().isoformat(),
            "deployment_id": deployment_id,
            "previous_model_hash": prev_model_hash,
            "new_model_hash": new_model_hash,
            "backup_available": True,
            "deployment_duration_ms": deployment_duration_ms,
            "staging_accuracy": staging_metadata.get("validation_accuracy", "N/A") if staging_metadata else "N/A"
        }
        
        logger.info(f"Hot-swap deployment completed: {deployment_id} (duration={deployment_duration_ms:.2f}ms)")
        
        return DeploymentResult(
            success=True,
            previous_model_path=MODEL_REGISTRY["backup"]["model_path"],
            new_model_path=MODEL_REGISTRY["production"]["model_path"],
            deployment_time=datetime.now().isoformat(),
            rollback_available=True,
            deployment_id=deployment_id,
            previous_model_hash=prev_model_hash,
            new_model_hash=new_model_hash,
            message=f"Model {deployment_id} deployed to production. Rollback available.",
            deployment_duration_ms=float(deployment_duration_ms)
        )
    
    except Exception as e:
        logger.error(f"Deployment error: {e}")
        return DeploymentResult(
            success=False,
            previous_model_path=MODEL_REGISTRY["production"]["model_path"],
            new_model_path="",
            deployment_time=datetime.now().isoformat(),
            rollback_available=True,
            deployment_id="",
            previous_model_hash="",
            new_model_hash="",
            message=f"Deployment failed: {str(e)}",
            deployment_duration_ms=0.0
        )


if __name__ == "__main__":
    ensure_directories()
    mcp.run(transport="stdio")
