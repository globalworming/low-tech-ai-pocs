from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README.md
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements.txt
def load_requirements():
    requirements_path = this_directory / 'requirements.txt'
    if requirements_path.exists():
        with open(requirements_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="low-tech-ai-pocs",
    version="0.1.0",
    author="globalworming",
    author_email="",
    description="Low-tech AI proof of concepts for image processing and analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/globalworming/low-tech-ai-pocs",
    packages=find_packages(include=['image_processor*']),
    include_package_data=True,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    install_requires=load_requirements(),
    entry_points={
        'console_scripts': [
            'image-analyzer=image_processor.cli:main',
            'lowtech-ai=cli:main',
        ],
    },
    extras_require={
        'dev': [
            # TODO later: check if these are still needed
            'pytest>=6.0',
            'black>=21.5b2',
            'isort>=5.0',
            'mypy>=0.812',
        ],
    },
)
