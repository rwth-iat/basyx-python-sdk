import setuptools

with open("README.md", "r", encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name="basyx-python-sdk",
    version="0.1.0",
    author="The Eclipse BaSyx Authors",
    description="The Eclipse BaSyx Python SDK, an implementation of the Asset Administration Shell for Industry 4.0 systems",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/eclipse-basyx/basyx-python-sdk",
    packages=setuptools.find_packages(exclude=["test", "test.*"]),
    zip_safe=False,
    package_data={
        "basyx": ["py.typed"],
        "basyx.aas.examples.data": ["TestFile.pdf"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
    ],
    entry_points={
        'console_scripts': [
            "aas-compliance-check = basyx.aas.compliance_tool.cli:main"
        ]
    },
    python_requires='>=3.8',
    install_requires=[
        'python-dateutil>=2.8,<3',
        'lxml>=4.2,<5',
        'urllib3>=1.26,<2.0',
        'pyecma376-2>=0.2.4',
    ],
    extras_require={
        'dev': [
            'pytest>=6.0',
            'flake8>=3.8',
            'coverage',
            # Add any other development dependencies here
        ],
    },
)
