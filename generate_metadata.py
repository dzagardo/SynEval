#!/usr/bin/env python3
"""
Metadata Generator for SynEval Experiments
==========================================
This script automatically generates metadata.json files by analyzing
the structure of CSV data files.

Usage:
    python generate_metadata.py --data-file data.csv --output metadata.json
    python generate_metadata.py --scan-directory experiments/data/
"""

import argparse
import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def infer_column_type(series: pd.Series) -> str:
    """
    Infer the semantic type of a column based on its data.
    
    Returns:
        One of: 'numerical', 'categorical', 'datetime', 'boolean'
    """
    # Check for datetime
    if pd.api.types.is_datetime64_any_dtype(series):
        return 'datetime'
    
    # Check for boolean
    if pd.api.types.is_bool_dtype(series):
        return 'boolean'
    
    # Check for numeric
    if pd.api.types.is_numeric_dtype(series):
        # Check if it's actually categorical (few unique values)
        unique_ratio = series.nunique() / len(series)
        if unique_ratio < 0.05 and series.nunique() < 20:
            return 'categorical'
        return 'numerical'
    
    # Try to parse as datetime
    try:
        pd.to_datetime(series.dropna().head(100), errors='raise')
        return 'datetime'
    except (ValueError, TypeError):
        pass
    
    # Default to categorical for strings
    return 'categorical'


def detect_pii_column(column_name: str, series: pd.Series) -> bool:
    """
    Detect if a column might contain personally identifiable information.
    
    This is a heuristic and should be reviewed manually.
    """
    column_lower = column_name.lower()
    
    # Common PII indicators in column names
    pii_indicators = [
        'name', 'email', 'phone', 'address', 'ssn', 'social_security',
        'credit_card', 'passport', 'license', 'user_id', 'customer_id',
        'account', 'ip_address', 'dob', 'birth', 'age'
    ]
    
    # Check column name
    for indicator in pii_indicators:
        if indicator in column_lower:
            return True
    
    # Check if column contains email-like values
    if series.dtype == 'object':
        sample = series.dropna().astype(str).head(100)
        if sample.str.contains('@').mean() > 0.5:
            return True
    
    return False


def detect_primary_key(df: pd.DataFrame) -> str:
    """
    Attempt to detect the primary key column.
    
    Returns:
        Column name that is likely the primary key, or None
    """
    for col in df.columns:
        col_lower = col.lower()
        
        # Check for common primary key names
        if col_lower in ['id', '_id', 'index', 'key', 'pk']:
            # Verify it has unique values
            if df[col].nunique() == len(df):
                return col
        
        # Check for unique sequential integers
        if pd.api.types.is_integer_dtype(df[col]):
            if df[col].nunique() == len(df) and df[col].is_monotonic_increasing:
                return col
    
    return None


def analyze_datetime_column(series: pd.Series) -> Dict[str, Any]:
    """
    Analyze a datetime column and extract format information.
    """
    # Try to infer the datetime format
    if pd.api.types.is_datetime64_any_dtype(series):
        return {
            'sdtype': 'datetime',
            'format': None  # Already datetime dtype
        }
    
    # Sample non-null values
    sample = series.dropna().head(100).astype(str)
    
    # Common datetime formats to try
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%Y/%m/%d',
        '%d-%m-%Y',
        '%m-%d-%Y',
        '%Y%m%d',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ',
    ]
    
    for fmt in formats:
        try:
            parsed = pd.to_datetime(sample, format=fmt, errors='raise')
            return {
                'sdtype': 'datetime',
                'format': fmt
            }
        except (ValueError, TypeError):
            continue
    
    # If no format matched, return generic datetime
    return {
        'sdtype': 'datetime',
        'format': None
    }


def generate_metadata(data_file: Path, dataset_name: str = None,
                     description: str = None) -> Dict[str, Any]:
    """
    Generate metadata for a CSV file.
    
    Args:
        data_file: Path to the CSV file
        dataset_name: Optional name for the dataset
        description: Optional description
        
    Returns:
        Dictionary containing the metadata structure
    """
    logger.info(f"Analyzing: {data_file}")
    
    # Read the data
    try:
        df = pd.read_csv(data_file, nrows=10000)  # Sample first 10k rows
        logger.info(f"  Shape: {df.shape}")
    except Exception as e:
        logger.error(f"Failed to read CSV: {e}")
        raise
    
    # Generate dataset name if not provided
    if dataset_name is None:
        dataset_name = data_file.stem
    
    # Generate description if not provided
    if description is None:
        description = f"Dataset generated from {data_file.name}"
    
    # Detect primary key
    primary_key = detect_primary_key(df)
    if primary_key:
        logger.info(f"  Detected primary key: {primary_key}")
    else:
        logger.warning("  No primary key detected")
    
    # Build column metadata
    columns = {}
    
    for col in df.columns:
        col_type = infer_column_type(df[col])
        is_pii = detect_pii_column(col, df[col])
        
        if is_pii:
            logger.warning(f"  Detected potential PII column: {col}")
        
        # Base column info
        col_info = {
            'sdtype': col_type,
            'pii': is_pii
        }
        
        # Add primary key flag
        if col == primary_key:
            col_info['is_primary_key'] = True
        
        # Add datetime format if applicable
        if col_type == 'datetime':
            datetime_info = analyze_datetime_column(df[col])
            if datetime_info['format']:
                col_info['format'] = datetime_info['format']
        
        # Add categorical info if applicable
        if col_type == 'categorical':
            unique_values = df[col].nunique()
            col_info['num_unique_values'] = unique_values
            
            # Include value list if small number of categories
            if unique_values <= 20:
                col_info['categories'] = df[col].dropna().unique().tolist()
        
        columns[col] = col_info
    
    # Build complete metadata
    metadata = {
        'dataset_name': dataset_name,
        'description': description,
        'num_rows': len(df),
        'num_columns': len(df.columns),
        'columns': columns
    }
    
    if primary_key:
        metadata['primary_key'] = primary_key
    
    logger.info(f"  Metadata generated for {len(columns)} columns")
    
    return metadata


def save_metadata(metadata: Dict[str, Any], output_file: Path):
    """Save metadata to a JSON file."""
    with open(output_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Metadata saved to: {output_file}")


def scan_directory(directory: Path):
    """Scan a directory and generate metadata for all CSV files."""
    logger.info(f"Scanning directory: {directory}")
    
    csv_files = list(directory.rglob("*.csv"))
    logger.info(f"Found {len(csv_files)} CSV files")
    
    for csv_file in csv_files:
        # Skip if metadata already exists
        metadata_file = csv_file.parent / f"{csv_file.stem}_metadata.json"
        
        if metadata_file.exists():
            logger.info(f"Skipping {csv_file.name} (metadata exists)")
            continue
        
        try:
            # Generate metadata
            metadata = generate_metadata(
                csv_file,
                dataset_name=csv_file.stem,
                description=f"Dataset from {csv_file.parent.name}/{csv_file.name}"
            )
            
            # Save metadata
            save_metadata(metadata, metadata_file)
            
        except Exception as e:
            logger.error(f"Failed to process {csv_file}: {e}")
            continue


def validate_metadata(metadata_file: Path, data_file: Path = None):
    """Validate a metadata file against its data file."""
    logger.info(f"Validating: {metadata_file}")
    
    # Load metadata
    try:
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load metadata: {e}")
        return False
    
    # Check required fields
    required_fields = ['dataset_name', 'columns']
    for field in required_fields:
        if field not in metadata:
            logger.error(f"Missing required field: {field}")
            return False
    
    # If data file provided, validate against it
    if data_file:
        try:
            df = pd.read_csv(data_file, nrows=100)
            
            # Check column names match
            metadata_cols = set(metadata['columns'].keys())
            data_cols = set(df.columns)
            
            if metadata_cols != data_cols:
                missing_in_metadata = data_cols - metadata_cols
                missing_in_data = metadata_cols - data_cols
                
                if missing_in_metadata:
                    logger.error(f"Columns in data but not metadata: {missing_in_metadata}")
                if missing_in_data:
                    logger.error(f"Columns in metadata but not data: {missing_in_data}")
                
                return False
            
            logger.info("✓ Metadata validates against data file")
            
        except Exception as e:
            logger.error(f"Failed to validate against data: {e}")
            return False
    
    logger.info("✓ Metadata structure is valid")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Generate metadata.json files for SynEval experiments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate metadata for a single file
  python generate_metadata.py --data-file data.csv --output metadata.json
  
  # Scan directory and generate metadata for all CSV files
  python generate_metadata.py --scan-directory experiments/data/
  
  # Validate existing metadata
  python generate_metadata.py --validate metadata.json --data-file data.csv
        """
    )
    
    parser.add_argument(
        '--data-file',
        type=str,
        help='Path to CSV data file'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output path for metadata.json (default: <data-file>_metadata.json)'
    )
    parser.add_argument(
        '--dataset-name',
        type=str,
        help='Name for the dataset (default: derived from filename)'
    )
    parser.add_argument(
        '--description',
        type=str,
        help='Description for the dataset'
    )
    parser.add_argument(
        '--scan-directory',
        type=str,
        help='Scan directory and generate metadata for all CSV files'
    )
    parser.add_argument(
        '--validate',
        type=str,
        help='Validate an existing metadata file'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force overwrite of existing metadata files'
    )
    
    args = parser.parse_args()
    
    # Mode 1: Scan directory
    if args.scan_directory:
        directory = Path(args.scan_directory)
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return 1
        
        scan_directory(directory)
        return 0
    
    # Mode 2: Validate metadata
    if args.validate:
        metadata_file = Path(args.validate)
        if not metadata_file.exists():
            logger.error(f"Metadata file not found: {metadata_file}")
            return 1
        
        data_file = Path(args.data_file) if args.data_file else None
        if data_file and not data_file.exists():
            logger.error(f"Data file not found: {data_file}")
            return 1
        
        if validate_metadata(metadata_file, data_file):
            return 0
        else:
            return 1
    
    # Mode 3: Generate metadata for single file
    if args.data_file:
        data_file = Path(args.data_file)
        if not data_file.exists():
            logger.error(f"Data file not found: {data_file}")
            return 1
        
        # Determine output path
        if args.output:
            output_file = Path(args.output)
        else:
            output_file = data_file.parent / f"{data_file.stem}_metadata.json"
        
        # Check if output exists
        if output_file.exists() and not args.force:
            logger.error(f"Output file exists: {output_file} (use --force to overwrite)")
            return 1
        
        # Generate metadata
        try:
            metadata = generate_metadata(
                data_file,
                dataset_name=args.dataset_name,
                description=args.description
            )
            save_metadata(metadata, output_file)
            
            # Validate
            if validate_metadata(output_file, data_file):
                logger.info("✓ Metadata generation successful!")
                return 0
            else:
                logger.error("✗ Generated metadata failed validation")
                return 1
                
        except Exception as e:
            logger.error(f"Failed to generate metadata: {e}")
            return 1
    
    # No valid mode specified
    parser.print_help()
    return 1


if __name__ == '__main__':
    exit(main())