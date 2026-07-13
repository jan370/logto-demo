# Logto OIDC Flow Demo

Eine kleine Flask-Demo, die den OIDC Authorization Code Flow bewusst in getrennten Schritten zeigt:

1. Bei Logto anmelden und Authorization Code anzeigen
2. Code serverseitig gegen Tokens tauschen
3. Access Token introspektieren und `active`, `sub` sowie Claims anzeigen
4. Token widerrufen und die Logto-Browsersitzung beenden

## Konfiguration

Die Anwendung benoetigt diese Umgebungsvariablen:

```text
LOGTO_ISSUER=https://tenant.logto.app/oidc
LOGTO_CLIENT_ID=...
LOGTO_CLIENT_SECRET=...
```

Secrets duerfen nicht in das Repository oder in das Docker-Image geschrieben werden.

## Lokal starten

Eine `.env`-Datei mit den drei Variablen anlegen und danach ausfuehren:

```shell
docker compose up --build
```

Die Demo ist dann unter `http://localhost:3001` erreichbar.
