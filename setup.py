from setuptools import setup, find_packages

setup(
    name="langgraph-codegen",           # Package name on PyPI
    version="v0.1.10",
    description="Generate graph code from DSL for LangGraph framework", 
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Johannes Johannsen",
    author_email="johannes.johannsen@gmail.com",
    url="https://github.com/jojohannsen/langgraph-codegen",
packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
