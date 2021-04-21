import setuptools
from importlib.machinery import SourceFileLoader
import os

dirname = os.path.dirname(__file__)
path_version = os.path.join(dirname, "ipr_service/_version.py")
version = SourceFileLoader('version', path_version).load_module()

setuptools.setup(
    name='ipr_service',
    version=version.__version__,
    description='IPR',
    author='Pantelis Mitropoulos',
    author_email='pmitropoulos@getmap.gr',
    license='MIT',
    packages=setuptools.find_packages(exclude=('tests*',)),
    package_data={'ipr_service': [
        'logging.conf'
    ]},
    python_requires='>=3.7',
    zip_safe=False,
)
