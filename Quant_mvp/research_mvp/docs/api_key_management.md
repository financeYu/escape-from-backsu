# API Key Management

Research ingestion loads API-related environment variables from the parent
Project API management folder without storing secret values in this repository.

Default lookup location:

```text
C:\Users\jjaew\Project\api_management\.env
```

Supported file names are `.env`, `api_keys.env`, `api-keys.env`, and
`keys.env`. Other `.env` files are not checked for API keys by default.

The loader only imports these allowlisted names by default:

```text
OPENALEX_API_KEY
OPENALEX_MAILTO
SEMANTIC_SCHOLAR_API_KEY
CROSSREF_PLUS_API_TOKEN
CROSSREF_MAILTO
```

Existing process environment values win over file values. To allow additional
local-only names, set `MASTER_MVP_API_KEY_ENV_VARS` to a comma-separated list.
To disable automatic loading, set `MASTER_MVP_API_KEYS_AUTOLOAD=0`.

Do not commit the parent API management file or any local `.env` file. The
research ingestion code returns only loaded variable names and source paths;
it does not print secret values.
