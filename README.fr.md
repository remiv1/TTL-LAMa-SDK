# Tests d'intégration du SDK

Le fichier `compose.test.yml` teste le SDK Python contre deux instances
TTL-LAMa : l'une utilise l'authentification interne et un backend WireGuard
accessible par SSH ; l'autre utilise Dex pour l'authentification OIDC.

Les tests créent un utilisateur, attribuent un profil et vérifient la création,
la configuration et la révocation d'un bail. Ils vérifient aussi l'attente puis
l'approbation d'une autorisation OIDC de type appareil et la connexion obtenue.
Les comptes et secrets de ce Compose sont réservés aux tests.

## Prérequis

- Un clone du projet TTL-LAMa contenant les sous-modules `sdk` et `cli`.
- Podman Compose et la capacité `NET_ADMIN` pour le conteneur WireGuard.
- L'accès aux images nécessaires et à l'index Python pour construire les images.

Le Compose utilise la configuration Dex du projet parent et construit le backend
WireGuard depuis le sous-module CLI. Par défaut, il utilise l'image serveur
`ghcr.io/remiv1/ttl-lama:latest`. Pour tester une autre image déjà disponible,
définissez `TTL_LAMA_SDK_SERVER_IMAGE` avant de lancer les commandes.

## Exécution

Depuis la racine du dépôt SDK, les trois suites peuvent être lancées séparément :

```sh
./scripts/test-unit.sh
./scripts/test-oidc.sh
./scripts/test-vpn.sh
```

Le lanceur unitaire comprend le test contre Flask. Chaque lanceur accepte `-t` suivi d'un sélecteur pytest pour limiter la sélection. Les suites utilisent des projets Compose distincts et peuvent être exécutées en parallèle :

```sh
make -j3 test
```

Les conteneurs et réseaux créés par les scripts sont arrêtés à leur sortie ; les volumes nommés ne sont pas supprimés. Les services ne publient aucun port sur l'hôte. Si l'environnement Podman rootless bloque les contrôles de santé à cause du réglage OOM, définissez `TTL_LAMA_TEST_OOM_SCORE_ADJ=1000` avant le lancement.

## Distribution Python

Dans un environnement virtuel Python 3.12 ou ultérieur, installez les outils de publication depuis la racine du dépôt SDK :

```sh
python -m pip install './python[release]'
make build
make package-check
```

`make check` exécute les trois suites et vérifie les archives. `make publish` effectue ces vérifications puis publie sur PyPI ; il nécessite un jeton fourni dans la variable d'environnement `TWINE_PASSWORD`. Ne placez pas ce jeton dans les fichiers du dépôt ni dans les journaux.
