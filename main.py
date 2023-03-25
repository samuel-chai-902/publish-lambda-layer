from os import makedirs
from json import dumps
from time import time
from pip import main
from shutil import make_archive, rmtree
from os.path import exists, expanduser, dirname
from argparse import ArgumentParser
from boto3 import Session
from sys import version_info


parser = ArgumentParser()
parser.add_argument('requirements', help="The path to the requirements.txt file.")
parser.add_argument('region', help="The region you want to publish the lambda layer to.")
parser.add_argument('output', help='The directory of the output file containing the ARNs of the lambda layers.')
args = vars(parser.parse_args())

req_file = expanduser(args["requirements"])
output_file = expanduser(args["output"])
working_dir = "/tmp/working{}".format(time())
region = args["region"]

layer_arns = {}
client = Session(region_name=region).client("lambda")


if not exists(req_file):
    raise FileNotFoundError("The file {} does not exist.".format(req_file))

makedirs(dirname(output_file), exist_ok=True)

runtime = "python{}.{}".format(version_info.major, version_info.major)


with open(req_file, "r") as file:
    for line in file:
        line = line.replace("\n", "").replace(" ", "")

        package_name = line.split(">")[0].split("<")[0].split("=")[0]
        parent_location = "{}/{}".format(working_dir, package_name)

        # Create the location of the dependencies and the location of the zip location
        zip_location = "{}/zip".format(parent_location)
        general_package_location = "{}/package".format(parent_location)
        required_package_location = "{}/python".format(general_package_location)

        # Install the dependencies as is required in a folder called python
        main(['install', f"{line}", "--target", required_package_location])

        zip_file = "{}/{}.zip".format(zip_location, package_name)
        make_archive(zip_file.replace(".zip", ""), 'zip', "{}/".format(general_package_location))

        with open(zip_file, "rb") as f:
            response = client.publish_layer_version(
                LayerName=package_name,
                Content={
                    "ZipFile": f.read(),
                },
                CompatibleRuntimes=[runtime],
                Description=line,
            )

            layer_arns[package_name] = response["LayerVersionArn"]


open(output_file, "w").write(dumps(layer_arns))
print(layer_arns)
rmtree(working_dir)