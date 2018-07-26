import setuptools


with open("README.rst", "rt", encoding="utf8") as f:
    read_me = f.read()


setuptools.setup(
    author="Adam Cunnington",
    author_email="adamcunnington.info@gmail.com",
    classifiers=(
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only"
    ),
    description="Streamly is a very simple yet powerful wrapper for streams.",
    license="MIT",
    long_description=read_me,
    long_description_content_type="text/x-rst",
    name="Streamly",
    project_urls={
        "Documentation": "https://streamly.readthedocs.io"
    },
    py_modules=["streamly"],
    python_requires=">=3.1",
    url="https://github.com/adamcunnington/Streamly",
    version="0.3"
)
