import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    # Metadata
    name='apeep',
    version='0.3',
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
        'numpy>=1.17',          # array operations
        'scikit-image>=0.16',   # image manipulation
        'PyYaml',               # configuration file
        'av==6.2.0',            # 'video' file reading
        #'lycon',               # image saving
        'Pillow',               # image saving
        'opencv-python',        # image saving
        'pandas'                # dataframe manipulation
    ]
    extras_require={
        'semantic': ['Detectron2']   # object detection for semantic pipeline
        'psd_masks': [
            'pytoshop',         # Photoshop image saving (1.1.0 works on mac, 1.2.0 works on linux)
            'packbits'          # to save compressed Photoshop files (not explicitely required by pytoshop but should be)
        ]
    }
)
