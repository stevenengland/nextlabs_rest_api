## Dotfiles Extension
the setup of this devcontainer supports that you bring in your own dotfiles from a public GitHub repository. To use this feature, you need to add the following configuration to your local settings.json (not the project settings):

```json
{
  "dotfiles.repository": "your-github-id/your-dotfiles-repo",
  "dotfiles.targetPath": "~/dotfiles",
  "dotfiles.installCommand": "install.sh"
}
```
## Docker Compose Override

This devcontainer also supports a docker-compose.override.yml file, which allows you to customize the Docker Compose configuration without modifying the original docker-compose.yml file. To use this feature, simply create a docker-compose.override.yml file in the .devcontainer directory with your desired overrides. For example, you can add additional services, change environment variables, or modify volumes. The docker-compose.override.yml file will be automatically picked up and applied when you start the devcontainer.
