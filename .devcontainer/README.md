## Dotfiles Extension
the setup of this devcontainer supports that you bring in your own dotfiles from a public GitHub repository. To use this feature, you need to add the following configuration to your local settings.json (not the project settings):

```json
{
  "dotfiles.repository": "your-github-id/your-dotfiles-repo",
  "dotfiles.targetPath": "~/dotfiles",
  "dotfiles.installCommand": "install.sh"
}
```
## Password-gated sudo (optional)

By default the `vscode` user has passwordless sudo (`NOPASSWD:ALL`), so any
process running as `vscode` — including an autonomous agent — can become root
with no friction. To require a password for `sudo` instead, run once in a
real terminal:

```bash
.devcontainer/harden-sudo.sh
```

It prompts you for a password (read from the terminal, **never stored in any
image layer**), sets it as the `vscode` login password via the existing
passwordless sudo, then rewrites `/etc/sudoers.d/vscode` to drop `NOPASSWD`.
After it runs, `sudo` requires the password you typed. The script refuses to
run non-interactively and is idempotent.

Caveat: during container setup `vscode` keeps passwordless sudo (post-create
needs it), so this cannot be cryptographically "human-only" — it is "first to
lock it wins." Run it yourself, early, right after setup.

To undo: a human with the password can restore `NOPASSWD:ALL` in
`/etc/sudoers.d/vscode`, or re-lock the account with `sudo passwd -l vscode`.

## Docker Compose Override

This devcontainer also supports a docker-compose.override.yml file, which allows you to customize the Docker Compose configuration without modifying the original docker-compose.yml file. To use this feature, simply create a docker-compose.override.yml file in the .devcontainer directory with your desired overrides. For example, you can add additional services, change environment variables, or modify volumes. The docker-compose.override.yml file will be automatically picked up and applied when you start the devcontainer.
