from setuptools import setup, find_packages

setup(
    name="langgraph-codegen",           # Package name on PyPI
    version="0.1.0",                    # Initial version
    description="Generate graph code from DSL for LangGraph framework", 
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Johannes Johannsen",        # Your name
    author_email="johannes.johannsen@gmail.com",  # Replace with your email
    url="https://github.com/jojohannsen/langgraph-codegen",  # GitHub repo
    packages=find_packages(),           # Automatically discover modules
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
