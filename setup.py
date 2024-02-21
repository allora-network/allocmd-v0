from setuptools import setup, find_packages

setup(
    name='allocmd',
    version='0.1.25',
    author='Upshot Technologies',
    author_email='tobi@upshot.xyz',
    description='A CLI tool for creating Allora Chain Worker Nodes',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'allocmd': ['templates/*.*'],
        '': ['*.j2', '*.txt', '*.rst']
    },
    install_requires=[
        'click',
        'docker',
        'pyyaml',
        'jinja2',
        'PyYAML',
        'termcolor',
    ],
    entry_points='''
        [console_scripts]
        allocmd=allocmd.cli:cli
    ''',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
)
