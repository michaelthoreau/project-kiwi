from setuptools import setup
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()
VERSION = '0.3.2'

setup(
  name = 'projectkiwi',
  packages = ['projectkiwi'],
  version = VERSION,
  license='MIT',
  description = 'Python tools for project-kiwi.org',
  long_description=long_description,
  long_description_content_type='text/markdown',
  author = 'Michael Thoreau',
  author_email = 'michael@project-kiwi.org',
  url = 'https://github.com/michaelthoreau/projectkiwi',
  keywords = ['GIS', 'ML', 'OTHERBUZZWORDS'],
  python_requires='>=3.3',
  classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ]
)