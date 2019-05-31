from setuptools import setup
import setuptools


setup(
    name='hello',
    packages=['hello'],
    package_data={'': ['script.sh']},
    entry_points={"console_scripts": ["hello = hello:main"]},
)
