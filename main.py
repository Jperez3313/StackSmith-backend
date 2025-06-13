from fastapi import FastAPI
from pydantic import BaseModel
import yaml
from fastapi.responses import JSONResponse

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:3000",  # your frontend URL, adjust as needed
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # allow frontend origins here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Define the expected input structure
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


@app.post("/generate")
def generate_spack_yaml(request: StackRequest):
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
            spec_str += f" % {pkg.compiler}"
        else:
            spec_str += f" % {request.compiler}"
        spack_env["spack"]["specs"].append(spec_str)

    yaml_output = yaml.dump(spack_env, sort_keys=False)
    return JSONResponse(content={"spack_yaml": yaml_output})

