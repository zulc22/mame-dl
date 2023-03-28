from setuptools import setup

setup(
    entry_points={
        "console_scripts": [
            "mame-dl=mame_dl:cli",
        ],
    },
)