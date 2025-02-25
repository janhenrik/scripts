#!/bin/bash

# Parse the optional -m argument
model="claude-3.5-sonnet"
if [[ $1 == "-m" && -n $2 ]]; then
  model="$2"
fi

curl -s "https://hn.algolia.com/api/v1/items/$1" | \
  jq -r 'recurse(.children[]) | .author + ": " + .text' | \
  llm -m "$model" -s 'Summarize the themes of the opinions expressed here.
  For each theme, output a markdown header.
  Include direct "quotations" (with author attribution) where appropriate.
  You MUST quote directly from users when crediting them, with double quotes.
  Fix HTML entities. Output markdown. Go long.' | \
tee /tmp/hn_summary.md && qlmanage -p /tmp/hn_summary.md
