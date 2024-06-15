from setuptools import setup

setup(
	name='networkMapper',
	py_modules=['networkMapper'],
	entry_points={
	'console_scripts': ['networkMapper = networkMapper:cli'],},
	long_description=open('README.md').read(),
	install_requires=['graphviz'],
	version="1.1.1"
)
