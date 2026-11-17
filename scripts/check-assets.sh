#!/usr/bin/env bash
# Fails when README.md or the site reference an image/asset that is not a file
# in this repository. Remote image hosts rot (the original README lost every
# picture to expired Discord CDN links), so all media must live in the repo.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

files=(README.md)
while IFS= read -r f; do files+=("$f"); done < <(find site docs -type f \( -name '*.html' -o -name '*.md' \) 2>/dev/null | sort)

fail=0
for f in "${files[@]}"; do
  [[ -f "$f" ]] || { echo "MISSING FILE: $f"; fail=1; continue; }
  dir="$(dirname "$f")"
  # src="..." attributes plus markdown ![alt](target) images
  refs="$(
    { grep -oE '(src|poster|data-src)="[^"]+"' "$f" | sed -E 's/^[a-z-]+="//; s/"$//'
      grep -oE '!\[[^]]*\]\([^)]+\)' "$f" | sed -E 's/^!\[[^]]*\]\(//; s/\)$//; s/ +"[^"]*"$//'
    } || true
  )"
  while IFS= read -r ref; do
    [[ -z "$ref" ]] && continue
    if [[ "$ref" =~ ^(https?:)?// ]]; then
      # Scripts from a CDN are allowed; media is not.
      if [[ "$ref" =~ \.(js|mjs)(\?.*)?$ ]]; then continue; fi
      echo "REMOTE ASSET: $f -> $ref"; fail=1; continue
    fi
    [[ "$ref" =~ ^(data:|#) ]] && continue
    path="${ref%%[?#]*}"
    path="${path//%20/ }"
    if [[ ! -e "$dir/$path" ]]; then
      echo "BROKEN LOCAL ASSET: $f -> $ref"; fail=1
    fi
  done <<< "$refs"
done

if (( fail )); then
  echo "FAIL: asset references are not self-contained"; exit 1
fi
echo "OK: all asset references resolve inside the repository (${#files[@]} files checked)"
