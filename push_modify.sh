#!/bin/bash
git add .
if [ -n "$1" ]
then
  note=$1
else
  note="some modify"
fi
git commit -m "$note"
git push -u origin main
