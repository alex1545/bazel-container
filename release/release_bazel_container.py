"""Starts the Bazel container release process
"""

import imp
import os
import shlex
import subprocess
import re

from util import get_git_root
from distutils.version import StrictVersion

GIT_ROOT = get_git_root()   # /usr/local/google/home/alexmogi/repos/alex1545/bazel-container
BAZEL_SHA_MAP_FILE = os.path.join(GIT_ROOT, "container/common/bazel/version.bzl")

BAZEL_GCS_PATH = "gs://bazel/"

BAZEL_CONTAINER_RELEASE_BRANCH = "bazel-container-release"

def main():
  # print versions_and_shas.CURR_VERSIONS_AND_SHAS["bazel"]["version"]
  # print versions_and_shas.CURR_VERSIONS_AND_SHAS["bazel"]["sha"]

  # read current version and sha from container/common/bazel/version.bzl
  curr_bazel_version, curr_bazel_sha = get_curr_bazel_version_and_sha()

  # get the latest Bazel version
  latest_bazel_version = get_latest_bazel_version()

  # in case couldn't find any released Bazel version (maybe if path changes)
  if latest_bazel_version is None:
  	return

  # get the latest Bazel version installer's sha
  latest_bazel_sha = get_latest_bazel_sha(latest_bazel_version)
  # print(latest_bazel_sha)

  # condition on which need to make code changes
  if curr_bazel_version != latest_bazel_version or curr_bazel_sha != latest_bazel_sha:
    print("Need to release new container")
    print("Bazel version: " + curr_bazel_version + " -> " + latest_bazel_version)
    print("Bazel installer sha: " + curr_bazel_sha + " -> " + latest_bazel_sha)

    # create the right branch locally first
    # - git checkout -b branchName

    # make code changes in container/common/bazel/version.bzl (add new version to sha mapping)
    # the code change relies on the line number where to insert code
    latest_bazel_version_to_sha_mapping = '    "' + latest_bazel_version + '": "' + latest_bazel_sha + '",\n'
    insert_line_to_file(GIT_ROOT + "/container/common/bazel/version.bzl", latest_bazel_version_to_sha_mapping, -1)

    # push changes to designated branch on GitHub (using local credentials)
    # - git add GIT_ROOT + "/container/common/bazel/version.bzl"
    # - git commit -m "Bazel update. Version: old -> new; Installer sha256: old -> new"
    # - git push origin branchName
    # - git branch -d branchName

    # create PR (add alex1545 as reviewer)



  # if different, make code changes and push to GitHub (Louhi will continue from there)

  # when finished, if release didn't happen for some reason, need to revert code changes
  # (maybe can close PR to undo this and then pull)

  # when released new container also want to update current version to latest

def get_curr_bazel_version_and_sha():
  """Return the current Bazel version and sha"""

  bazel_version_sha_map = imp.load_source("version", BAZEL_SHA_MAP_FILE)

  bazel_versions = bazel_version_sha_map.BAZEL_VERSION_SHA256S.keys()
  bazel_versions.sort(key=StrictVersion)
  curr_version = bazel_versions[-1]

  return curr_version, bazel_version_sha_map.BAZEL_VERSION_SHA256S[curr_version]

def get_latest_bazel_version():
  """Return the latest Bazel version from GCS"""

  # get bazel GCS bucket content
  bazel_bucket_content = subprocess.check_output(["gsutil", "ls", BAZEL_GCS_PATH]).split()

  # get rid of unrelated dirs (not containing a Bazel installer)
  regex = re.compile(r'^gs://bazel/\d+(\.\d+)*/$')
  bazel_versions = [path[len(BAZEL_GCS_PATH):-1] for path in bazel_bucket_content if regex.search(path)]
  bazel_versions.sort(key=StrictVersion, reverse=True)

  # find the newest released version (bazel version path with a release dir)
  for version in bazel_versions:
  	try:
  	  subprocess.check_call(["gsutil", "ls", BAZEL_GCS_PATH + version + "/release"])
  	  return version
  	  break
  	except:
  	   print("Bazel " + version + " is not released yet. Skipping.")

  return None

def get_latest_bazel_sha(version):
  """Return the latest Bazel installer's sha"""

  return subprocess.check_output(["gsutil", "cat", BAZEL_GCS_PATH + version + "/release/bazel-" + version + "-installer-linux-x86_64.sh.sha256"])[:64]

def insert_line_to_file(file_path, line_text, line_num):
  file = open(file_path, "r")
  content = file.readlines()
  file.close()

  content.insert(line_num, line_text)

  file = open(file_path, "w")
  content = "".join(content)
  file.write(content)
  file.close()

if __name__ == "__main__":
  main()
