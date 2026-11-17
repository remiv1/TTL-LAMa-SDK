#!/usr/bin/env bash

SUITE=unit
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/test-common.sh" "$@"

section "$GREEN" "Construction du conteneur de tests"
"${COMPOSE[@]}" build sdk-tests
COMPOSE_STARTED=true
"${COMPOSE[@]}" run --rm --no-deps sdk-tests python -c 'import api.bootstrap'
run_tests python/tests/test_client.py python/tests/test_resources.py python/tests/test_server_integration.py