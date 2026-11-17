#!/usr/bin/env bash

SUITE=oidc
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/test-common.sh" "$@"

section "$GREEN" "Construction du conteneur de tests"
"${COMPOSE[@]}" build sdk-tests
section "$BLUE" "Demarrage de Dex et du serveur OIDC"
COMPOSE_STARTED=true
"${COMPOSE[@]}" up -d --wait --wait-timeout 120 oidc-server
run_tests python/tests/integration/test_compose.py::test_oidc_device_authorization_with_dex