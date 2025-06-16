# StackSmith Backend

This is the backend API for StackSmith. It accepts software stack input (like compilers and specs), and generates a `spack.yaml` file for reproducible HPC software environments.

## Features

- FastAPI-powered API
- Converts JSON input to valid Spack environment YAML
- Supports compiler and version pinning
- Ready for future expansion (e.g., spack install automation)

## Software Dependencies

### 1. **Spack**
StackSmith requires [Spack](https://spack.io) to be installed and available 

## Getting Started

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

