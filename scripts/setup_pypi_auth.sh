#!/bin/bash
# Interactive script to set up PyPI authentication

set -e

echo "=========================================="
echo "PyPI Authentication Setup"
echo "=========================================="
echo ""
echo "This script will help you set up ~/.pypirc for PyPI uploads."
echo "You'll need API tokens from:"
echo "  - TestPyPI: https://test.pypi.org/manage/account/token/"
echo "  - Production: https://pypi.org/manage/account/token/"
echo ""

# Check if .pypirc already exists
if [ -f ~/.pypirc ]; then
    echo "⚠️  ~/.pypirc already exists!"
    read -p "Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
    # Backup existing file
    cp ~/.pypirc ~/.pypirc.backup.$(date +%Y%m%d_%H%M%S)
    echo "Backed up existing file to ~/.pypirc.backup.*"
fi

echo ""
read -p "Enter your TestPyPI token (pypi-...): " TEST_TOKEN
read -p "Enter your production PyPI token (pypi-...): " PROD_TOKEN

# Validate tokens start with pypi-
if [[ ! $TEST_TOKEN =~ ^pypi- ]]; then
    echo "⚠️  Warning: TestPyPI token doesn't start with 'pypi-'"
fi

if [[ ! $PROD_TOKEN =~ ^pypi- ]]; then
    echo "⚠️  Warning: Production token doesn't start with 'pypi-'"
fi

# Create .pypirc file
cat > ~/.pypirc << EOF
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = ${PROD_TOKEN}

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = ${TEST_TOKEN}
EOF

# Set secure permissions
chmod 600 ~/.pypirc

echo ""
echo "✅ .pypirc file created at ~/.pypirc"
echo ""
echo "You can now upload packages:"
echo "  TestPyPI:  python -m twine upload --repository testpypi dist/*"
echo "  Production: python -m twine upload dist/*"
echo ""
echo "Or use the publish script:"
echo "  ./scripts/publish.sh test"
echo "  ./scripts/publish.sh prod"

