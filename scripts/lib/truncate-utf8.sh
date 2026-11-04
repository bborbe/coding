#!/usr/bin/env bash
# Shared field-bounding helper for the mechanical funnel scripts.
#
# truncate_utf8_file <limit-bytes> <input-file> <output-file>
#
# Mirrors the extraction the callers used before this change: trailing
# newlines are stripped (the old `$(...)` did that), then the value is
# bounded to <limit-bytes> on a UTF-8 rune boundary. A value that was cut
# ends with `…[truncated, original <N> bytes]`, where <N> is the pre-cut
# byte length after the trailing-newline strip. The marker is part of the
# string value, so it survives a consumer that re-marshals a fixed field set.
#
# python3 is already a hard dependency of both callers (they use it for
# START_MS/END_MS), so the byte-accurate cut adds no new runtime dependency.

truncate_utf8_file() {
  local limit="$1" in="$2" out="$3"
  local size

  if ! size=$(wc -c < "$in"); then
    printf 'error: truncate-utf8: cannot read %s\n' "$in" >&2
    return 1
  fi

  # Common case: the field is small. Strip trailing newlines exactly as the
  # previous `$(...)` extraction did and write it through unchanged.
  if [ "$size" -le "$limit" ]; then
    if ! printf '%s' "$(cat "$in")" > "$out"; then
      printf 'error: truncate-utf8: cannot write %s\n' "$out" >&2
      return 1
    fi
    return 0
  fi

  # Oversized: cut on a rune boundary. The bound is in bytes, so a plain
  # character slice is not enough; back off over continuation bytes and drop
  # a lead byte whose sequence is incomplete at the cut.
  if ! python3 - "$limit" "$in" "$out" <<'PY'
import sys

limit = int(sys.argv[1])
with open(sys.argv[2], 'rb') as fh:
    data = fh.read().rstrip(b'\n')

if len(data) <= limit:
    out = data
else:
    cut = data[:limit]
    j = len(cut) - 1
    while j >= 0 and (cut[j] & 0xC0) == 0x80:
        j -= 1
    if j < 0:
        cut = b''
    else:
        lead = cut[j]
        if lead < 0x80:
            need = 1
        elif (lead & 0xE0) == 0xC0:
            need = 2
        elif (lead & 0xF0) == 0xE0:
            need = 3
        elif (lead & 0xF8) == 0xF0:
            need = 4
        else:
            need = 1
        have = len(cut) - j
        cut = cut[:j + need] if have >= need else cut[:j]
    out = cut + ('…[truncated, original %d bytes]' % len(data)).encode('utf-8')

with open(sys.argv[3], 'wb') as fh:
    fh.write(out)
PY
  then
    printf 'error: truncate-utf8: cannot process %s\n' "$in" >&2
    return 1
  fi
}
