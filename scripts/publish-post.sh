#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <filename> <date-prefix>" >&2
  exit 1
fi

filename="$1"
date_prefix="$2"
src="pending-posts/$filename"

if [ ! -f "$src" ]; then
  echo "missing source file: $src" >&2
  exit 1
fi

mkdir -p _posts
dest="_posts/${date_prefix}-${filename}"

if [ -e "$dest" ]; then
  echo "destination already exists: $dest" >&2
  exit 1
fi

mv "$src" "$dest"
echo "published: $dest"
