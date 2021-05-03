import setuptools
import io
import os


def read_file(filename):
    with open(filename) as fp:
        return fp.read().strip()


def read_requirements(filename):
    return [line.strip() for line in read_file(filename).splitlines()
            if not line.startswith('#')]


REQUIRED = read_requirements('requirements.txt')
here = os.path.abspath(os.path.dirname(__file__))

with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = '\n' + f.read()

setuptools.setup(
    name="aroay_translate",
    version="1.3",
    author="hwpchn",
    author_email="13692839895@163.com",
    description="scrapy的异步翻译，最准确的翻译器",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hwpchn/AroayTranslate.git",
    packages=setuptools.find_packages(),
    install_requires=REQUIRED,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
