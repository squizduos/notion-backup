#!/bin/sh
set -u -e

# Set through the github action:
# - GITHUB_TOKEN
# - NOTION_TOKEN
# - FORCE_BRANCH
# - GITHUB_REPOSITORY
# - NOTION_FILE_TOKEN

NOW=$(date "+%Y-%m-%d %T")
PAGES="$1"
REPO="/app/repo"
OUTPUT="$REPO/$2"

if [ $# -lt 2 ]; then
  echo 1>&2 "$0: not enough arguments, provide <pages> <output-dir>"
  exit 2
fi

if [ -n "$FORCE_BRANCH" ]; then
  BRANCH="$FORCE_BRANCH"
else
  BRANCH="${GITHUB_REF##*/}"
fi

# Use this user email https://github.com/actions
git config --global user.email github-actions[bot]@users.AsahiMoon.github.com
git config --global user.name "Notion Exporter"
git config --global github.token "${GITHUB_TOKEN}"

echo ":: Cloning github.com/${GITHUB_REPOSITORY} ${BRANCH} into ${REPO}"
git clone --branch "${BRANCH}" "https://${GITHUB_ACTOR}:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}" "$REPO"

echo ":: Exporting ${PAGES} into ${OUTPUT}"
python /app/notion_backup.py -page "${PAGES}" -token "${NOTION_TOKEN}" -file_token "${NOTION_FILE_TOKEN}" -output "${OUTPUT}"

find "${OUTPUT}"

set +e
cd "${REPO}" && git add "$2" && git commit -am "Pulled content from notion at ${NOW}"
set -e

if [ "$?" -ne "0" ]; then
    echo ":: Nothing to commit"
    exit 0
else
  echo ":: Push the commit"
  git push "https://${GITHUB_ACTOR}:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" "${BRANCH}"
fi


