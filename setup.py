import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    # Metadata
    name='apeep',
    version='0.2',
    description='Process ISIIS images without a peep',
    url='https://github.com/jiho/apeep',
    author='Jean-Olivier Irisson',
    author_email='irisson@normalesup.org',
    license='GPLv3',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Development Status :: 3 - Alpha'
    ],
    # Content
    packages=setuptools.find_packages(exclude=['docs', 'tests']),
    entry_points={
        'console_scripts': ['apeep = apeep.__main__:main']
    },
    package_data={
        'apeep': ['config.yaml'],
    },
    python_requires='>=3.6',
    install_requires=[
        'numpy',
        'scikit-image',
        'PyYaml',
        'av',
    ]
)
