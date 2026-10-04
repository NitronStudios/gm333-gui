from setuptools import setup, find_packages

setup(
    name="gm333-gui",
    version="1.0.0",
    description="Ant Esports GM333 Linux Hardware & Music Sync GUI Controller",
    author="Ant Esports GM333 Linux Project",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "numpy>=1.20.0",
        "Pillow>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "gm333-gui=gm333gui.__main__:main",
        ],
    },
    classifiers=[
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: System :: Hardware",
    ],
)
