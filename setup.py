from distutils.core import setup
setup(
  name = 'projectkiwi',         # How you named your package folder (MyLib)
  packages = ['projectkiwi'],   # Chose the same as "name"
  version = '0.1',      # Start with a small number and increase it with every change you make
  license='MIT',        # Chose a license from here: https://help.github.com/articles/licensing-a-repository
  description = 'Python tools for project-kiwi.org',   # Give a short description about your library
  author = 'Michael Thoreau',                   # Type in your name
  author_email = 'michael@project-kiwi.org',      # Type in your E-Mail
  url = 'https://github.com/michaelthoreau/projectkiwi',   # Provide either the link to your github or to your website
  download_url = 'https://github.com/user/reponame/archive/v_01.tar.gz',    # I explain this later on
  keywords = ['GIS', 'ML', 'OTHERBUZZWORDS'],   # Keywords that define your package best
  install_requires=['requests'],
  python_requires='>=3.3',
  classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ]
)