# SDK Python TTL-LAMa

Ce client synchrone utilise l'API v1 de TTL-LAMa. Il ne nécessite pas la CLI. Il couvre l'authentification, les comptes, les équipements, les profils et les baux. La configuration globale et l'interface web ne sont pas incluses.

## Installation

Depuis un environnement virtuel Python 3.12 ou ultérieur :

```sh
python -m pip install ./sdk/python
```

Pour développer le SDK depuis la racine du dépôt SDK :

```sh
python -m pip install -e './python[test]'
python -m pytest python/tests
```

## Connexion et utilisation

```python
from getpass import getpass
from ttlama_sdk import TTLLama

with TTLLama("https://ttl-lama.example") as ttl:
    ttl.login("admin", getpass("Mot de passe : "))
    utilisateur = ttl.user.get("UUID_UTILISATEUR")
    attribution = ttl.user.assign_profile(utilisateur["id"], 1)
    print(attribution["profile_id"])
    ttl.auth.logout()
```

La connexion interne récupère automatiquement le jeton CSRF et conserve le cookie associé pendant l'authentification. Les appels suivants utilisent le jeton Bearer. Le client accepte aussi un jeton existant :

```python
with TTLLama("https://ttl-lama.example", token=token) as ttl:
    identite = ttl.me.get()
    profils = ttl.me.overview()["profiles"]
```

Le jeton est disponible dans `ttl.token`. Il reste en mémoire ; le SDK ne le stocke pas et ne l'affiche pas. L'appelant doit le protéger. `logout()` révoque la session courante et efface le jeton du client. Changer son mot de passe via `ttl.me.change_password(ancien, nouveau)` révoque toutes les sessions et efface également le jeton courant. Fermer le client seul ne révoque pas la session. Les opérations administrateur exigent un compte actif avec `is_admin` à `true`.

## Ressources

Les méthodes retournent des dictionnaires ou des listes correspondant au JSON de l'API ; les opérations sans contenu retournent `None`. Les valeurs comme les dates restent des chaînes. Les champs acceptés pour la création et la modification sont ceux de l'API ; la validation métier est effectuée par le serveur.

| Objet | Méthodes |
| --- | --- |
| `ttl.user` | `list`, `get`, `create`, `update`, `delete`, `profiles`, `assign_profile`, `unassign_profile` |
| `ttl.device` | `list`, `get`, `update`, `block`, `delete` |
| `ttl.lease` | `list`, `get`, `revoke` |
| `ttl.profile` | `list`, `get`, `create`, `update`, `delete` |
| `ttl.me` | `get`, `overview`, `change_password` |
| `ttl.me.devices` | `list`, `get`, `create`, `delete` |
| `ttl.me.leases` | `list`, `get`, `create`, `configuration`, `revoke` |
| `ttl.auth` | `csrf`, `logout`, `oidc_exchange`, `oidc_device`, `oidc_poll` |

Les filtres des listes administrateur sont passés en arguments nommés, par exemple `ttl.lease.list(status="active", user="UUID")`. Les modifications acceptent les champs en arguments nommés :

```python
resultat = ttl.user.create("alice", email="alice@example.org")
# En mode interne sans mot de passe fourni : resultat contient user et generated_password.
ttl.user.update(resultat["user"]["id"], enabled=True)
```

Avec un mot de passe explicitement fourni, la réponse de création est directement l'utilisateur ; elle ne contient jamais ce mot de passe. En mode externe, un mot de passe omis ne crée pas d'identifiant interne. Une politique de profil ancienne peut être `None`.

Un utilisateur peut créer son équipement et demander un bail :

```python
device = ttl.me.devices.create("portable", "CLE_PUBLIQUE_CLIENT")
lease = ttl.me.leases.create(device["id"], profile_id=1, duration="1h")
configuration = ttl.me.leases.configuration(lease["id"])
```

Générez et conservez la clé privée WireGuard localement. Le SDK ne doit recevoir que la clé publique ; complétez le modèle `configuration_template` localement. Le filtrage des destinations par profil dépend d'une configuration réseau externe adaptée, pas de WireGuard seul.

## Authentification OIDC

`ttl.auth.oidc_device()` retourne notamment `device_code`, `user_code`, `verification_uri`, `expires_in` et `interval`. Présentez l'URI et le code utilisateur à l'utilisateur, gardez `device_code` confidentiel, puis appelez `ttl.auth.oidc_poll(device_code)` en respectant l'intervalle fourni et en l'augmentant pour `slow_down`. Les états `denied` et `expired` terminent le parcours. L'état `complete` enregistre automatiquement le jeton Bearer. Pour un ticket CLI à usage unique, `ttl.auth.oidc_exchange(ticket)` l'échange et enregistre aussi le jeton. Le SDK ne lance pas de navigateur et n'effectue pas de boucle de consultation à votre place.

## Erreurs et délais

Les erreurs dérivent de `TTLamaError`. `APIError` expose `status_code` et, quand le serveur le fournit, `lease_id`. Les erreurs HTTP 400, 401, 403, 404, 409 et 503 ont respectivement les classes `ValidationError`, `AuthenticationError`, `AuthorizationError`, `NotFoundError`, `ConflictError` et `ProvisioningError`. Les erreurs réseau ou réponses JSON invalides utilisent `APIError`. Les corps d'erreur ne sont pas inclus dans les messages d'exception.

Le délai HTTP par défaut est de 5 secondes ; les opérations de création ou révocation de bail utilisent 60 secondes pour attendre le backend VPN. Ils sont configurables avec `timeout` et `lease_timeout`. Un `503` ou un délai réseau ne prouve pas qu'aucune opération n'a été engagée : vérifiez l'état du bail avant de réessayer. Le SDK ne relance pas automatiquement les mutations.
