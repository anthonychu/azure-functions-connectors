from setuptools import setup, find_namespace_packages

setup(
    name="azure-functions-connectors",
    version="0.1.0",
    description="Azure managed connector bindings for Azure Functions",
    packages=find_namespace_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "azure-functions>=1.17.0",
        "azure-identity>=1.15.0",
        "azure-storage-blob>=12.19.0",
        "azure-storage-queue>=12.9.0",
        "aiohttp>=3.8.0",
    ],
)
