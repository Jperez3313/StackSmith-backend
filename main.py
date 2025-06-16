import subprocess
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import yaml
import re

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PackageSpec(BaseModel):
    name: str
    version: str | None = None
    variants: str | None = None
    compiler: str | None = None

class StackRequest(BaseModel):
    specs: list[PackageSpec]
    compiler: str
    mpi: str | None = None
    target: str | None = None
    os: str | None = None

@app.get("/variants/{package_name}")
def get_package_variants(package_name: str):
    try:
        result = subprocess.run(
            ["spack", "info", package_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            print(f"Spack command failed: {result.stderr}")
            return JSONResponse(content={"error": result.stderr}, status_code=400)
        
        print(f"Spack info output for {package_name}:")
        print(result.stdout)
        
        variants = []
        lines = result.stdout.splitlines()
        
        in_variants_section = False
        in_when_block = False
        
        for i, line in enumerate(lines):
            # Look for the start of variants section
            if "Variants:" in line or "variants:" in line.lower():
                print(f"Found Variants section at line {i}: {line}")
                in_variants_section = True
                continue
            
            if in_variants_section:
                stripped_line = line.strip()
                
                if (stripped_line and 
                    not line.startswith(("    ", "\t", "when ")) and 
                    ":" in stripped_line and 
                    any(keyword in stripped_line for keyword in ["Dependencies", "Licenses", "Description", "Homepage", "Maintainers"])):
                    print(f"End of variants section at line {i}: {stripped_line}")
                    break
                
                if not stripped_line or stripped_line.startswith("when "):
                    if stripped_line.startswith("when "):
                        in_when_block = True
                        print(f"Skipping when block starting at line {i}: {stripped_line}")
                    continue
                
                if in_when_block:
                    if line.startswith("    ") and not line.startswith("      "):
                        in_when_block = False
                        print(f"Exiting when block at line {i}")
                    else:
                        continue
                
                if (line.startswith("    ") and 
                    not line.startswith("        ") and 
                    "[" in stripped_line and "]" in stripped_line):
                    variant_match = re.match(r'\s*([a-zA-Z][a-zA-Z0-9_-]*)\s*\[', line)
                    if variant_match:
                        variant_name = variant_match.group(1)
                        if (variant_name and 
                            variant_name not in variants and 
                            len(variant_name) > 1 and
                            variant_name.lower() not in ['name', 'default', 'allowed', 'values', 'description', 'true', 'false', 'when']):
                            variants.append(variant_name)
                            print(f"Found variant: {variant_name}")
                
                variant_matches = re.findall(r'[+~]([a-zA-Z0-9_-]+)', line)
                for variant_match in variant_matches:
                    if variant_match and variant_match not in variants:
                        variants.append(variant_match)
                        print(f"Found variant with prefix: {variant_match}")
        
        if not variants:
            print("No variants found, showing lines in variants section for debugging:")
            in_variants_section = False
            for i, line in enumerate(lines):
                if "Variants:" in line:
                    in_variants_section = True
                    continue
                if in_variants_section:
                    print(f"Line {i}: '{line}'")
                    if (line.strip() and 
                        not line.startswith(("    ", "\t", "when ")) and 
                        ":" in line.strip() and 
                        any(keyword in line for keyword in ["Dependencies", "Licenses", "Description", "Homepage", "Maintainers"])):
                        break
        
        print(f"Final variants for {package_name}: {variants}")
        return {"variants": variants}
        
    except subprocess.TimeoutExpired:
        print(f"Spack info command timed out for package: {package_name}")
        return JSONResponse(content={"error": "Command timed out"}, status_code=408)
    except FileNotFoundError:
        print("Spack command not found. Make sure Spack is installed and in PATH.")
        return JSONResponse(content={"error": "Spack not found. Please ensure Spack is installed and in your PATH."}, status_code=500)
    except Exception as e:
        print(f"Exception in get_package_variants: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/generate")
def generate_spack_yaml(request: StackRequest):
    try:
        spack_env = {
            "spack": {
                "specs": [],
                "packages": {},
                "compilers": [],
            }
        }
        
        for pkg in request.specs:
            spec_str = pkg.name
            if pkg.version:
                spec_str += f"@{pkg.version}"
            if pkg.variants:
                spec_str += f" {pkg.variants}"
            if pkg.compiler:
                spec_str += f" %{pkg.compiler}"
            else:
                spec_str += f" %{request.compiler}"
            spack_env["spack"]["specs"].append(spec_str)
        
        # Add MPI if specified
        if request.mpi:
            spack_env["spack"]["packages"]["all"] = {
                "providers": {
                    "mpi": [request.mpi]
                }
            }
        
        # Add target architecture if specified
        if request.target:
            for i, spec in enumerate(spack_env["spack"]["specs"]):
                spack_env["spack"]["specs"][i] += f" target={request.target}"
        
        yaml_output = yaml.dump(spack_env, sort_keys=False, default_flow_style=False)
        
        return {"spack_yaml": yaml_output}
        
    except Exception as e:
        print(f"Exception in generate_spack_yaml: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/health")
def health_check():
    """Health check endpoint to verify the service is running"""
    return {"status": "healthy", "message": "Spack YAML generator is running"}

@app.get("/")
def root():
    """Root endpoint with basic information"""
    return {
        "name": "Spack YAML Generator API",
        "version": "1.0.0",
        "endpoints": {
            "variants": "/variants/{package_name}",
            "generate": "/generate",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
