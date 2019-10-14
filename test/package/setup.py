import setuptools

from setuptools import setup

setup(
    name="hello",
    packages=["hello"],
    package_data={"": ["script.sh"]},
    entry_points={"console_scripts": ["hello = hello:main"]},
)
