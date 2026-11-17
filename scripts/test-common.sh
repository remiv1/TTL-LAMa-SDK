#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SDK_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$SDK_DIR/compose.test.yml"
PROJECT="ttlama-sdk-${SUITE}-$$-${RANDOM}"
COMPOSE=(podman compose -p "$PROJECT" -f "$COMPOSE_FILE")
TEST_SELECTORS=()
COMPOSE_STARTED=false
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
RESET='\033[0m'
export PODMAN_COMPOSE_WARNING_LOGS=false

while (($#)); do
  case "$1" in
    -t)
      if (($# < 2)) || [[ -z "$2" || "$2" == -* ]]; then
        printf 'Usage: %s [-t test_selector]...\n' "$0" >&2
        exit 2
      fi
      TEST_SELECTORS+=("$2")
      shift 2
      ;;
    -h|--help)
      printf 'Usage: %s [-t test_selector]...\n' "$0"
      exit 0
      ;;
    *)
      printf 'Option inconnue : %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

section() {
  local color="$1" title="$2" columns=80 inner left right
  if [[ -t 1 ]] && command -v tput >/dev/null 2>&1; then
    columns=$(tput cols 2>/dev/null || printf '80')
  fi
  if ((columns < ${#title} + 12)); then
    columns=$((${#title} + 12))
  fi
  inner=$((columns - 10 - ${#title}))
  left=$((inner / 2))
  right=$((inner - left))
  printf '\n%b' "$color"
  printf '%*s\n' "$columns" '' | tr ' ' '='
  printf '=== |%*s%s%*s| ===\n' "$left" '' "$title" "$right" ''
  printf '%*s\n%b' "$columns" '' "$RESET" | tr ' ' '='
}

cleanup() {
  local exit_code=$?
  trap - EXIT
  if [[ "$COMPOSE_STARTED" == true ]]; then
    section "$YELLOW" "Arret des conteneurs de test"
    if ! "${COMPOSE[@]}" down >/dev/null 2>&1; then
      printf '\033[0;31m%s\033[0m\n' '[TESTS] Echec du nettoyage du projet Compose.' >&2
      if ((exit_code == 0)); then
        exit_code=1
      fi
    fi
  fi
  exit "$exit_code"
}
trap cleanup EXIT

run_tests() {
  local -a selectors=("$@")
  if ((${#TEST_SELECTORS[@]})); then
    selectors=("${TEST_SELECTORS[@]}")
  fi
  section "$RED" "Lancement des tests : $SUITE"
  COMPOSE_STARTED=true
  "${COMPOSE[@]}" run --rm --no-deps sdk-tests \
    python -m pytest -v --color=yes -ra -p no:cacheprovider "${selectors[@]}"
  printf '\033[0;32m%s\033[0m\n' '[TESTS] Tests executes avec succes.'
}