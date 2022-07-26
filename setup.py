from setuptools import setup
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
  name = 'projectkiwi',         # How you named your package folder (MyLib)
  packages = ['projectkiwi'],   # Chose the same as "name"
  version = '0.3.0',      # Start with a small number and increase it with every change you make
  license='MIT',        # Chose a license from here: https://help.github.com/articles/licensing-a-repository
  description = 'Python tools for project-kiwi.org',   # Give a short description about your library
  long_description=long_description,
  long_description_content_type='text/markdown',
  author = 'Michael Thoreau',                   # Type in your name
  author_email = 'michael@project-kiwi.org',      # Type in your E-Mail
  url = 'https://github.com/michaelthoreau/projectkiwi',   # Provide either the link to your github or to your website
  download_url = 'https://github.com/michaelthoreau/projectkiwi/archive/refs/tags/v0.3.0.tar.gz',    # I explain this later on
  keywords = ['GIS', 'ML', 'OTHERBUZZWORDS'],   # Keywords that define your package best
  install_requires=['requests', 'numpy', 'pillow'],
  python_requires='>=3.3',
  classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ]
)