import asyncio
import json
import logging
import os
from pathlib import Path

import numpy as np
from mcp.client.stdio import StdioServerParameters
from mcp.client.session import ClientSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_SERVER_PATH = str(Path(__file__).parent / "src" / "guardian_server.py")


async def demonstrate_drift_detection() -> None:
    """Demonstrate data drift detection workflow."""
    logger.info("Starting Drift Detection Demonstration")
    
    training_data = np.random.normal(loc=0, scale=1, size=(1000, 5))
    
    normal_production = np.random.normal(loc=0, scale=1, size=(100, 5))
    
    drifted_production = np.random.normal(loc=2, scale=1, size=(100, 5))
    
    feature_names = ["feature_0", "feature_1", "feature_2", "feature_3", "feature_4"]
    
    async with ClientSession(
        StdioServerParameters(
            command="python",
            args=[MODEL_SERVER_PATH]
        )
    ) as session:
        
        logger.info("Testing Normal Production Data (No Drift Expected)")
        result_normal = await session.call_tool(
            "monitor_data_drift",
            {
                "production_data_samples": normal_production.tolist(),
                "training_data_baseline": training_data.tolist(),
                "feature_names": feature_names,
                "drift_threshold": 0.05
            }
        )
        
        logger.info(f"Normal Data Drift Result: {json.dumps(result_normal, indent=2)}")
        
        logger.info("\nTesting Drifted Production Data (Drift Expected)")
        result_drifted = await session.call_tool(
            "monitor_data_drift",
            {
                "production_data_samples": drifted_production.tolist(),
                "training_data_baseline": training_data.tolist(),
                "feature_names": feature_names,
                "drift_threshold": 0.05
            }
        )
        
        logger.info(f"Drifted Data Drift Result: {json.dumps(result_drifted, indent=2)}")


async def demonstrate_model_retraining() -> None:
    """Demonstrate model retraining workflow."""
    logger.info("\n\nStarting Model Retraining Demonstration")
    
    np.random.seed(42)
    
    X_train = np.random.randn(500, 5)
    y_train = (X_train[:, 0] + X_train[:, 1] > 0).astype(int)
    
    feature_names = ["feature_0", "feature_1", "feature_2", "feature_3", "feature_4"]
    
    async with ClientSession(
        StdioServerParameters(
            command="python",
            args=[MODEL_SERVER_PATH]
        )
    ) as session:
        
        logger.info("Triggering Model Retraining")
        retrain_result = await session.call_tool(
            "trigger_model_retraining",
            {
                "new_training_data": X_train.tolist(),
                "new_training_labels": y_train.tolist(),
                "feature_names": feature_names,
                "validation_split": 0.2,
                "random_state": 42
            }
        )
        
        logger.info(f"Retraining Result: {json.dumps(retrain_result, indent=2)}")


async def demonstrate_model_comparison() -> None:
    """Demonstrate model evaluation and comparison."""
    logger.info("\n\nStarting Model Comparison Demonstration")
    
    np.random.seed(42)
    
    X_test = np.random.randn(200, 5)
    y_test = (X_test[:, 0] + X_test[:, 1] > 0).astype(int)
    
    async with ClientSession(
        StdioServerParameters(
            command="python",
            args=[MODEL_SERVER_PATH]
        )
    ) as session:
        
        logger.info("Comparing Production vs Staging Model")
        comparison_result = await session.call_tool(
            "judge_model_performance",
            {
                "test_data": X_test.tolist(),
                "test_labels": y_test.tolist(),
                "compare_with_production": True
            }
        )
        
        logger.info(f"Model Comparison: {json.dumps(comparison_result, indent=2)}")


async def demonstrate_deployment() -> None:
    """Demonstrate model hot-swap deployment."""
    logger.info("\n\nStarting Deployment Demonstration")
    
    async with ClientSession(
        StdioServerParameters(
            command="python",
            args=[MODEL_SERVER_PATH]
        )
    ) as session:
        
        logger.info("Executing Hot-Swap Deployment")
        deployment_result = await session.call_tool(
            "deploy_model_hot_swap",
            {}
        )
        
        logger.info(f"Deployment Result: {json.dumps(deployment_result, indent=2)}")


async def demonstrate_full_pipeline() -> None:
    """Demonstrate complete self-healing pipeline."""
    logger.info("\n\n" + "="*80)
    logger.info("FULL SELF-HEALING ML PIPELINE DEMONSTRATION")
    logger.info("="*80)
    
    np.random.seed(42)
    
    training_data = np.random.normal(loc=0, scale=1, size=(1000, 5))
    
    drifted_production = np.random.normal(loc=1.5, scale=1.2, size=(200, 5))
    
    feature_names = ["feature_0", "feature_1", "feature_2", "feature_3", "feature_4"]
    
    X_train_new = np.vstack([training_data, drifted_production])
    y_train_new = (X_train_new[:, 0] + X_train_new[:, 1] > 0).astype(int)
    
    X_test = np.random.normal(loc=1.5, scale=1.2, size=(300, 5))
    y_test = (X_test[:, 0] + X_test[:, 1] > 0).astype(int)
    
    async with ClientSession(
        StdioServerParameters(
            command="python",
            args=[MODEL_SERVER_PATH]
        )
    ) as session:
        
        logger.info("\nSTEP 1: Detect Data Drift")
        logger.info("-" * 40)
        drift_result = await session.call_tool(
            "monitor_data_drift",
            {
                "production_data_samples": drifted_production.tolist(),
                "training_data_baseline": training_data.tolist(),
                "feature_names": feature_names,
                "drift_threshold": 0.05
            }
        )
        logger.info(f"Drift Detected: {drift_result['has_drift']}")
        logger.info(f"Summary: {drift_result['summary']}")
        
        if drift_result["has_drift"]:
            
            logger.info("\nSTEP 2: Trigger Model Retraining")
            logger.info("-" * 40)
            retrain_result = await session.call_tool(
                "trigger_model_retraining",
                {
                    "new_training_data": X_train_new.tolist(),
                    "new_training_labels": y_train_new.tolist(),
                    "feature_names": feature_names,
                    "validation_split": 0.2,
                    "random_state": 42
                }
            )
            logger.info(f"Retraining Success: {retrain_result['success']}")
            logger.info(f"Validation Accuracy: {retrain_result['validation_accuracy']:.4f}")
            logger.info(f"Samples Used: {retrain_result['samples_used']}")
            
            
            logger.info("\nSTEP 3: Judge Model Performance")
            logger.info("-" * 40)
            comparison_result = await session.call_tool(
                "judge_model_performance",
                {
                    "test_data": X_test.tolist(),
                    "test_labels": y_test.tolist(),
                    "compare_with_production": True
                }
            )
            logger.info(f"Production Accuracy: {comparison_result['production_accuracy']:.4f}")
            logger.info(f"New Model Accuracy: {comparison_result['new_model_accuracy']:.4f}")
            logger.info(f"Improvement: {comparison_result['accuracy_improvement']:.4f}")
            logger.info(f"Should Deploy: {comparison_result['should_deploy']}")
            logger.info(f"Summary: {comparison_result['summary']}")
            
            
            if comparison_result["should_deploy"]:
                logger.info("\nSTEP 4: Hot-Swap Deployment")
                logger.info("-" * 40)
                deployment_result = await session.call_tool(
                    "deploy_model_hot_swap",
                    {}
                )
                logger.info(f"Deployment Success: {deployment_result['success']}")
                logger.info(f"Message: {deployment_result['message']}")
                logger.info(f"Rollback Available: {deployment_result['rollback_available']}")
                
                logger.info("\n" + "="*80)
                logger.info("PIPELINE COMPLETE: Model successfully updated to production!")
                logger.info("="*80)
            else:
                logger.info("\nPipeline halted: New model does not meet performance threshold")


async def main() -> None:
    """Run all demonstrations."""
    try:
        await demonstrate_drift_detection()
        await demonstrate_model_retraining()
        await demonstrate_model_comparison()
        await demonstrate_deployment()
        await demonstrate_full_pipeline()
        
        logger.info("\n\nAll demonstrations completed successfully!")
    
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
