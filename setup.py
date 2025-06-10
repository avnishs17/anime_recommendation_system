from setuptools import setup,find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()


__version__ = "0.0.0"

REPO_NAME = "anime_recommendation_system"
AUTHOR_USER_NAME = "avnishs17"
SRC_REPO = "anime_recommendation_system"
AUTHOR_EMAIL = "avnish1708@gmail.com"


setup(
    name=SRC_REPO,
    version=__version__,
    author=AUTHOR_USER_NAME,
    author_email=AUTHOR_EMAIL,
    description="Anime Recommendation System",
    packages=find_packages(),
    install_requires = requirements,
)