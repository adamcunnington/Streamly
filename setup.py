import setuptools


with open("README.rst") as f:
    readme = f.read()


with open("LICENSE") as f:
    license = f.read()


setuptools.setup(
    author="Adam Cunnington",
    author_email="adamcunnington.info@gmail.com",
    description="",
    install_requires=[],
    license=license,
    long_description=readme,
    name="Streamly",
    packages=setuptools.find_packages(exclude=("tests")),
    url="https://github.com/adamcunnington/Streamly",
    version="0.1"
)
