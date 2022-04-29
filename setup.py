from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='edf_api',
    packages=find_packages(include=['edf_api']),
    version='0.1.1',
    author='drosocode',
    license='MIT',
    description='API for EDF',
    url="https://github.com/droso-hass/edf-api",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=["aiohttp", "async_timeout", "lxml"],
    python_requires=">=3.7",
    project_urls={
        'Documentation': 'https://edf-api.readthedocs.io/en/latest/',
        'Source': 'https://github.com/droso-hass/edf-api',
    },
)