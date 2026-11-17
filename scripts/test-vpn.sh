#!/usr/bin/env bash

SUITE=vpn
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/test-common.sh" "$@"

section "$GREEN" "Construction des conteneurs de tests"
"${COMPOSE[@]}" build wireguard-backend sdk-tests
section "$BLUE" "Demarrage du backend WireGuard et du serveur"
COMPOSE_STARTED=true
"${COMPOSE[@]}" up -d --wait --wait-timeout 120 server
run_tests python/tests/integration/test_compose.py::test_wireguard_lease_lifecycle