#!/bin/bash
set -e  # Exit on error

echo "===== Scholia Build Script for Render ====="

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements-web.txt

# Build frontend
echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "Build complete!"
