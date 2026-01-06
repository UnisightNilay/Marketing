#!/bin/bash
# Run Marketing Display Application with environment selection

echo "=========================================="
echo "Marketing Display Application"
echo "=========================================="
echo ""
echo "Select environment:"
echo "1) Development (local)"
echo "2) Staging"
echo "3) Production"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        ENVIRONMENT="development"
        ;;
    2)
        ENVIRONMENT="staging"
        ;;
    3)
        ENVIRONMENT="production"
        ;;
    *)
        echo "Invalid choice, using development"
        ENVIRONMENT="development"
        ;;
esac

echo ""
echo "Starting in $ENVIRONMENT mode..."
echo ""

# Export environment
export ENVIRONMENT=$ENVIRONMENT

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run the application
python3 app.py
