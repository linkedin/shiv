from setuptools import setup
import setuptools


setup(
    name='hello',
    packages=['hello'],
    entry_points={"console_scripts": ["hello = hello:main"]},
)
