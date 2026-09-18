#!/usr/bin/env bash
set -euo pipefail

## @just 74 Verification | Benchmark interactive shell startup time (10 runs default, pass N to override)

readonly ITERATIONS="${1:-10}"
readonly WARMUP=2
readonly REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
readonly README="$REPO_ROOT/README.md"

times=()

for ((i = 1; i <= WARMUP; i++)); do
    bash -ic exit 2>/dev/null
done

for ((i = 1; i <= ITERATIONS; i++)); do
    t=$({ TIMEFORMAT='%R'; time bash -ic exit 2>/dev/null; } 2>&1)
    times+=("$t")
    printf "  run %2d: %ss\n" "$i" "$t"
done

mapfile -t sorted < <(printf '%s\n' "${times[@]}" | sort -n)

min="${sorted[0]}"
max="${sorted[${#sorted[@]}-1]}"
median="${sorted[$(( ${#sorted[@]} / 2 ))]}"

sum=0
for t in "${times[@]}"; do
    sum=$(awk "BEGIN{printf \"%.3f\", $sum + $t}")
done
avg=$(awk "BEGIN{printf \"%.3f\", $sum / ${#times[@]}}")

printf "\n  %d runs (after %d warmup)\n" "$ITERATIONS" "$WARMUP"
printf "  min: %ss  median: %ss  avg: %ss  max: %ss\n" "$min" "$median" "$avg" "$max"

if awk "BEGIN{exit !($median > 0.5)}"; then
    printf "\n  ⚠ median > 0.5s — consider profiling with:\n"
    printf "    bash -x -ic exit 2>&1 | head -80\n"
fi

# Inject summary into README between bench markers
if [[ -f "$README" ]] && grep -q '<!-- bench:start -->' "$README"; then
    local_date=$(date +%Y-%m-%d)
    bench_line="$ITERATIONS runs — min: ${min}s · median: ${median}s · avg: ${avg}s · max: ${max}s (updated $local_date)"
    awk -v line="$bench_line" '
        /<!-- bench:start -->/ { print; print line; skip=1; next }
        /<!-- bench:end -->/   { skip=0 }
        !skip
    ' "$README" > "$README.tmp"
    mv "$README.tmp" "$README"
    printf "\n  ✓ README.md updated\n"
fi
