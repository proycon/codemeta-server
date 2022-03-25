#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    version='0.1.0',
    name='codemeta-server',
    license='GPL-3.0-only',
    description='API serving codemeta software metadata using codemeta and schema.org, provides a SPARQL endpoint',
    author='Maarten van Gompel',
    author_email='proycon@anaproy.nl',
    url='https://github.com/CLARIAH/tool-discovery',
    packages=find_packages(),
    python_requires='>=3.7.0',
    install_requires=open("requirements.txt", "r", encoding='utf-8').readlines(),
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    project_urls={
        "Issues": "https://github.com/CLARIAH/tool-discovery/issues",
        "Source Code": "https://github.com/CLARIAH/tool-discovery",
        "Releases": "https://github.com/CLARIAH/tool-discovery/releases"
    },
    entry_points={
        'console_scripts': [
            'codemeta-server=codemeta_server.main:main'
        ]
    },
)
