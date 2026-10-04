from setuptools import setup, find_packages

setup(
    name="detox-open-mouse-drivers",
    version="1.0.0",
    description="Detox Open Mouse Drivers - Linux Hardware & AI Music Sync Controller for Gaming Mice",
    author="NitronStudios & Linux Gaming Community",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "numpy>=1.20.0",
        "Pillow>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "detox-mouse=gm333gui.__main__:main",
            "detox-open-mouse=gm333gui.__main__:main",
            "gm333-gui=gm333gui.__main__:main",
        ],
    },
    classifiers=[
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: System :: Hardware",
    ],
)
