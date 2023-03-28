# mame-dl
Pet project to make downloading ROMs for MAME quicker and easier. Don't download anything with it that you don't have a legal right to!!! Nuh uh!!! *wags finger*

# Installation
Requirements:

- Python 3

- wget

To get Wget on Windows, to make mame-dl functional, the cleanest solution in my opinion is to install it with [Scoop](https://scoop.sh/) or [Chocolatey](https://chocolatey.org/), but you can also [download an .exe file from eternallybored.org](https://eternallybored.org/misc/wget/) and copy it to `C:\Windows\` or some other folder in the PATH environment variable as well.

## pip install, from GitHub (requires Git to be installed)
```
pip install "mame_dl @ git+https://github.com/zulc22/mame-dl"
```

## pip install, from .zip
Download a .zip from the 'Code' button on the top right of the GitHub page, click Download ZIP, extract it, and change your terminal's current directory to whichever folder from that ZIP containing the 'pyproject.toml' file. Then,
```
pip install -e .
```

# Usage
Type `mame-dl` in a terminal window for help.