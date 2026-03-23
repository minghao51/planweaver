#!/usr/bin/env python3
"""
Initialize models from YAML configuration into database.

Usage:
    uv run python scripts/maintenance/init_models.py
    uv run python scripts/maintenance/init_models.py --file data/models/custom_models.yaml
"""

import argparse
from pathlib import Path
import yaml
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from planweaver.db.models import AvailableModel  # noqa: E402
from planweaver.db.database import get_session, init_db, run_migrations  # noqa: E402


def load_models_from_yaml(yaml_path: str | Path) -> list[dict]:
    """Load model configurations from YAML file.

    Args:
        yaml_path: Path to YAML file containing model definitions

    Returns:
        List of model configuration dictionaries
    """
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)
        return data.get("models", [])


def init_models(models_data: list[dict], clear_existing: bool = False) -> int:
    """Initialize models in database.

    Args:
        models_data: List of model configuration dictionaries
        clear_existing: If True, remove all existing models first

    Returns:
        Number of models added
    """
    session = get_session()

    try:
        if clear_existing:
            print("Clearing existing models...")
            session.query(AvailableModel).delete()
            session.commit()

        added_count = 0
        updated_count = 0

        for model_config in models_data:
            model_id = model_config["id"]

            # Check if model already exists
            existing = session.query(AvailableModel).filter_by(model_id=model_id).first()

            pricing_info = model_config.get("pricing_info")

            if existing:
                # Update existing model
                existing.name = model_config["name"]
                existing.provider = model_config["provider"]
                existing.type = model_config["type"]
                existing.is_free = model_config.get("is_free", True)
                existing.context_length = model_config.get("context_length")
                existing.pricing_info = pricing_info
                existing.is_active = True
                updated_count += 1
                print(f"Updated: {model_config['name']}")
            else:
                # Create new model
                new_model = AvailableModel(
                    model_id=model_id,
                    name=model_config["name"],
                    provider=model_config["provider"],
                    type=model_config["type"],
                    is_free=model_config.get("is_free", True),
                    context_length=model_config.get("context_length"),
                    pricing_info=pricing_info,
                    is_active=True,
                )
                session.add(new_model)
                added_count += 1
                print(f"Added: {model_config['name']}")

        session.commit()
        print(f"\nSummary: {added_count} added, {updated_count} updated")
        return added_count + updated_count

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Initialize models from YAML into database")
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        default="data/models/default_models.yaml",
        help="Path to YAML file with model definitions",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all existing models before adding new ones",
    )

    args = parser.parse_args()

    # Initialize database first
    print("Initializing database...")
    init_db()
    run_migrations()
    print("Database ready\n")

    # Resolve path relative to project root
    yaml_path = Path(args.file)
    if not yaml_path.is_absolute():
        yaml_path = project_root / args.file

    if not yaml_path.exists():
        print(f"Error: File not found: {yaml_path}")
        sys.exit(1)

    print(f"Loading models from: {yaml_path}")
    models_data = load_models_from_yaml(yaml_path)
    print(f"Found {len(models_data)} model definitions\n")

    count = init_models(models_data, clear_existing=args.clear)
    print(f"\nSuccessfully processed {count} models")


if __name__ == "__main__":
    main()
