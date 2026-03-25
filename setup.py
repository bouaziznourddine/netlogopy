from setuptools import setup, find_packages
import codecs
import os

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    long_description = fh.read()

VERSION = '0.1.0'
DESCRIPTION = 'netlogopy: Bridge NetLogo and Python for advanced agent-based simulations'

setup(
    name="netlogopy",
    version=VERSION,
    author="Nourddine Bouaziz",
    author_email="nourddine.bouaziz.dz@gmail.com",
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Bouaziz19/netlogopy",
    project_urls={
        "Bug Tracker": "https://github.com/Bouaziz19/netlogopy/issues",
        "Source Code": "https://github.com/Bouaziz19/netlogopy",
    },
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "netlogopy": ["*.nlogo", "*.nls"],
    },
    python_requires=">=3.6",
    install_requires=["nl4py"],
    keywords=["python", "netlogo", "simulation", "multi-agent", "agent-based modeling", "ABM"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)

# Build and publish:
#   python -m build
#   twine upload dist/*
