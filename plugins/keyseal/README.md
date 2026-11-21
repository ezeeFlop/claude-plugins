# Keyseal for Claude Code and Codex

Configure a product from its source repository, maintain imported Lemon Squeezy products and distribute the project's official builds through Keyseal. Both clients install the same publisher code. Python 3.11 is selected by `uv`; the server uses the Python standard library.

## Claude Code

```sh
claude plugin marketplace add ezeeFlop/claude-plugins
claude plugin install keyseal@sponge-theory
```

## Codex

```sh
codex plugin marketplace add https://github.com/ezeeFlop/claude-plugins.git
codex plugin add keyseal-codex@sponge-theory-codex
```

Start a new session in the product repository. If the marketplace is already installed, refresh its snapshot first. Use `claude plugin marketplace update sponge-theory` or `codex plugin marketplace upgrade sponge-theory-codex`.

## Authentication

Use a Keyseal API key scoped to the organization and environment, with `catalog` and `files` rights. The server reads `KEYSEAL_API_KEY` from the launching environment or the default Keyseal CLI profile at `$XDG_CONFIG_HOME/keyseal/config.toml` (default `~/.config/keyseal/config.toml`, mode 0600). `KEYSEAL_PROFILE` selects a named profile. Only the official https://keyseal.io origin receives the credential. Keep it out of source control and client applications. A configured workstation can onboard subsequent products directly from the agent.

To use an existing key for one terminal session with bash or zsh, enter it in the hidden prompt, then launch the client from that terminal.

```sh
read -rs KEYSEAL_API_KEY
export KEYSEAL_API_KEY
```

Ask the agent to run `keyseal_context` and verify the publisher and environment before any write. For example, “Set up this application in my Keyseal Test catalogue. Use the website and icon from this repository and preview the offers.” For an existing application, ask it to match the imported product ID and preserve its current licences. After a successful Test run, use a Live credential and authorize the desired changes. A paid checkout becomes available when the offer is public and its price is synchronized with the publisher's Stripe Managed Payments account.

## Tools

| Tool | Result |
| --- | --- |
| `keyseal_context` | Verified organization, environment and scoped product identifiers |
| `keyseal_product` | Preview or apply product and offer changes, with immutable identity checks, purchase URLs and public signing keys |
| `keyseal_image` | Store an official local raster image and assign the Keyseal-hosted visual to its product |
| `keyseal_release` | Hash, upload and publish verified builds with the existing buyer coverage |

The server never returns management credentials or storage upload tickets. Existing paid licences, historic installations and checkout links can be preserved independently of catalogue enrichment.

## En français

Installez le plugin avec les commandes de votre client ci-dessus. Vérifiez l’organisation et Test ou Live avec `keyseal_context`. Dans le dépôt du produit, demandez par exemple « Prépare la fiche de cette application dans Keyseal Test avec son site et son visuel officiels. Montre-moi les offres avant publication. » Pour une application importée, indiquez son produit existant. Le plugin retrouve ses identifiants, publie les versions construites par le dépôt et restitue les clés publiques à embarquer. Les droits `catalog` et `files` suffisent pour ces opérations. [Guides de la plateforme](https://keyseal.io/fr/docs/).
