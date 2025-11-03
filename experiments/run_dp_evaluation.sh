# experiments/run_dp_evaluation.sh
#!/bin/bash

###############################################################################
# Differential Privacy Evaluation Runner - Bash Wrapper
# 
# This script provides a convenient interface to run the DP evaluation pipeline
# with various options and configurations.
###############################################################################

# Set script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
CONFIG_FILE="configs/cross_group_dp.yaml"
PARALLEL=true
WORKERS=4
LOG_LEVEL="INFO"
PYTHON_CMD="python3"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Run Differential Privacy evaluation experiments with SynEval

OPTIONS:
    -c, --config FILE       Path to configuration file (default: configs/cross_group_dp.yaml)
    -p, --parallel          Run experiments in parallel
    -w, --workers N         Number of parallel workers (default: 4)
    -l, --log-level LEVEL   Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
    -d, --dry-run           Show what would be executed without running
    -h, --help              Show this help message and exit

EXAMPLES:
    # Run with default configuration (sequential)
    $0

    # Run in parallel with 8 workers
    $0 --parallel --workers 8

    # Run with custom config and debug logging
    $0 --config my_config.yaml --log-level DEBUG

    # Dry run to see what would be executed
    $0 --dry-run

EOF
}

# Function to check dependencies
check_dependencies() {
    print_info "Checking dependencies..."
    
    # Check Python
    if ! command -v $PYTHON_CMD &> /dev/null; then
        print_error "Python 3 is not installed or not in PATH"
        return 1
    fi
    
    # Check required Python packages
    local missing_packages=()
    
    for package in numpy pandas yaml; do
        if ! $PYTHON_CMD -c "import $package" 2>/dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        print_warning "Missing Python packages: ${missing_packages[*]}"
        print_info "Install with: pip install ${missing_packages[*]}"
        return 1
    fi
    
    # Check if config file exists
    if [ ! -f "$PROJECT_ROOT/$CONFIG_FILE" ]; then
        print_error "Configuration file not found: $PROJECT_ROOT/$CONFIG_FILE"
        return 1
    fi
    
    print_success "All dependencies satisfied"
    return 0
}

# Function to run the evaluation
run_evaluation() {
    local cmd="$PYTHON_CMD $SCRIPT_DIR/run_dp_evaluation.py"
    cmd="$cmd --config $CONFIG_FILE"
    cmd="$cmd --log-level $LOG_LEVEL"
    
    if [ "$PARALLEL" = true ]; then
        cmd="$cmd --parallel --workers $WORKERS"
    fi
    
    print_info "Starting DP evaluation runner..."
    print_info "Configuration: $CONFIG_FILE"
    print_info "Parallel: $PARALLEL (Workers: $WORKERS)"
    print_info "Log level: $LOG_LEVEL"
    echo
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Run the command
    eval $cmd
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        print_success "Evaluation completed successfully"
    else
        print_error "Evaluation failed with exit code $exit_code"
    fi
    
    return $exit_code
}

# Parse command line arguments
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -w|--workers)
            WORKERS="$2"
            shift 2
            ;;
        -l|--log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
echo "============================================================"
echo "    Differential Privacy Evaluation Runner"
echo "============================================================"
echo

# Check dependencies
if ! check_dependencies; then
    print_error "Dependency check failed. Please install missing dependencies."
    exit 1
fi

# Dry run mode
if [ "$DRY_RUN" = true ]; then
    print_info "DRY RUN MODE - No experiments will be executed"
    echo
    print_info "Would execute:"
    cmd="$PYTHON_CMD $SCRIPT_DIR/run_dp_evaluation.py"
    cmd="$cmd --config $CONFIG_FILE"
    cmd="$cmd --log-level $LOG_LEVEL"
    
    if [ "$PARALLEL" = true ]; then
        cmd="$cmd --parallel --workers $WORKERS"
    fi
    
    echo "  $cmd"
    echo
    print_info "Working directory: $PROJECT_ROOT"
    print_info "Python interpreter: $PYTHON_CMD"
    exit 0
fi

# Run the evaluation
run_evaluation
exit_code=$?

# Show results location
if [ $exit_code -eq 0 ]; then
    echo
    print_info "Results saved to: $PROJECT_ROOT/reports/dp_evaluation/"
    print_info "View execution summary: $PROJECT_ROOT/reports/dp_evaluation/execution_summary.json"
fi

exit $exit_code