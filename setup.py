import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="Activation Connector for TikTok Ads",
    version="0.0.1",

    description="(SO9073) Solution guidance to assist AWS customers with automating the activation of TikTok Ads with custom audience data for selected TikTok Advertiser. It explores the stages of activating custom audience segments data created in AWS to deliver personalized ads in TikTok",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="rajeabh,bmaguiraz",

    package_dir={"": "lib/tiktok/packages"},
    packages=setuptools.find_packages(where="packages"),

    install_requires=[
        "aws-cdk-lib==2.38.1",
        "constructs>=10.0.0",
        "constructs>=11.0.0",
        "aws-cdk.aws-s3-deployment"
    ],

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: MIT-0",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
