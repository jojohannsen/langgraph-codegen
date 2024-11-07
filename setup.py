from setuptools import setup, find_packages

setup(
    name="langgraph-codegen",
    version="v0.1.13",
    description="Generate graph code from DSL for LangGraph framework", 
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Johannes Johannsen",
    author_email="johannes.johannsen@gmail.com",
    url="https://github.com/jojohannsen/langgraph-codegen",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        'langgraph_codegen': ['examples/*.graph'],
    },
    include_package_data=True,  # This tells setuptools to include files from MANIFEST.in
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'lgcodegen=langgraph_codegen.lgcodegen:main',
        ],
    },
)