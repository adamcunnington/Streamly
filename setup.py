import setuptools


with open("README.rst") as f:
    readme = f.read()


with open("LICENSE") as f:
    license = f.read()


setuptools.setup(
    author="Adam Cunnington",
    author_email="adamcunnington.info@gmail.com",
    classifiers=(
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only"
    ),
    description="",
    license=license,
    long_description=readme,
    name="Streamly",
    py_modules=["streamly"],
    url="https://github.com/adamcunnington/Streamly",
    version="0.1"
)
