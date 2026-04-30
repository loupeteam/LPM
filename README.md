# LPM

![version badge](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Floupeteam%2FLPM%2Fmain%2Fsrc%2Fversion.json&query=%24.version&label=version)

This tool is provided by Loupe.  
https://loupe.team  
info@loupe.team  
1-800-240-7042

## Installation
Install LPM by first [installing Python](https://docs.python.org/3/using/windows.html) and [Node](https://nodejs.org/en/download/), then downloading the latest version of the installer [here](https://loupe-lpm-assets.s3.us-west-2.amazonaws.com/releases/latest/LPM-Setup.exe). After running the installer, you can run `lpm` commands from your terminal of choice.

## Description

LPM is the Loupe Package Manager. This tool is designed to make it easy to interact with Loupe packages within the Automation Studio and Loupe UX ecosystems. It provides a command line interface for installing packages in a project, and for managing their lifecycle (version update, dependency checks, removal, etc).

## Documentation

Documentation for LPM use, including detailed installation instructions and use cases, can be found [here](https://loupeteam.github.io/LoupeDocs/tools/lpm.html). 

## Custom registries / additional scopes

LPM ships configured for the `@loupeteam` scope (backed by the `loupeteam` GitHub organization on `https://npm.pkg.github.com`). Other organizations can register their own GitHub-hosted scopes without modifying LPM source.

Create `~/.lpm/config.json` (or set `LPM_CONFIG_PATH` to point elsewhere):

```json
{
  "defaultScope": "@loupeteam",
  "scopes": {
    "@acme": {
      "org": "acme-corp",
      "registry": "https://npm.pkg.github.com"
    }
  }
}
```

Per-project overrides may be added under the `lpmConfig` key in a project's `package.json`:

```json
{
  "lpmConfig": {
    "scopes": {
      "@acme": { "org": "acme-corp", "registry": "https://npm.pkg.github.com" }
    }
  }
}
```

Behavior with extra scopes configured:
- `lpm install <name>` still auto-prefixes bare names with the **default** scope. To install from another scope, use the explicit name: `lpm install @acme/foo`.
- `lpm login` writes a `<scope>:registry=...` line in `~/.npmrc` for every configured scope. A single GitHub PAT covers all scopes hosted on `npm.pkg.github.com`.
- `lpm viewall` queries every configured scope's GitHub organization and prints a combined list with a `Scope` column.
- `lpm publish` is currently restricted to `@loupeteam` only. Multi-scope publishing is tracked as a future enhancement.

If no config file is present, LPM behaves identically to previous releases (loupeteam-only).

## Licensing
This project is licensed under the [MIT License](LICENSE.md). 
