# dotbot-crossplatform

Crossplatform linking plugin for [Dotbot](https://github.com/anishathalye/dotbot).

## Motivation

Currently, dotbot doesn't work very well on windows. Symlinking is difficult to get working, and 
file paths don't work as expected when syncing with windows and linux.

I have created a crossplatform plugin that currently builds off the default `link` task. Hopefully in 
the future I will add crossplatform versions of other default tasks such as `shell`.


## Scope

This was started to meet my own requirements for dotbot on windows and linux. If you would like to see changes
to meet your own workflow, please file an issue and I'll try to meet your needs.

## Installation

Add `dotbot-crossplatform` as a submodule of your dotfiles repository:

```sh
git submodule add git@github.com:msdrigg/dotbot-crossplatform.git
```

Update `install` script to enable the `dotbot-crontab` plugin. You can do this by replacing the last line of 
the script to include `--plugin-dir dotbot-crossplatform`. For example:

```bash
"${BASEDIR}/${DOTBOT_DIR}/${DOTBOT_BIN}" -d "${BASEDIR}" -c "${CONFIG}" --plugin-dir dotbot-crossplatform "${@}"
```

## Usage

Add a `crossplatform-link` task, or convert your existing `link` tasks to `crossplatform-link` tasks. 
The `crossplatform-link` task is built ontop of the `link` task, so much of the behavior is simliar. 
To make paths compatible for windows and linux, I use python's `os.path.normpath` to normalize both the
source and the destination paths (after globbing if applicable). This command will convert forward slashes
to backward slashes when using windows, so please use forward slashes to define paths in your `install.conf.yaml` file.

Also, sometimes I want to make different links depending on the platform, so `crossplatform-link` also accepts a list of
dictionaries instead of just a dictionary of links. Using a list of dictionaries, you can make multiple links to the 
same source (See item below for an example).

Additionally, symlinks don't work with windows under default conditions, so I added the `fallback_to_copy` parameter. This 
parameter will switch to copying the file if `os.symlink` fails. This parameter is best combined with `force: true`. 
Without `force`, the files will only copy over once, and then fail to update with all future linking.

Finally, I added the `platform` and `environment` conditions. These conditions will filter for platform or environmental
variables. A summary of all additional variables is presented below.

| Parameter | Change |
| --- | --- |
|`fallback_to_copy` | Copy the files into the destination if sym-linking fails. Best paired with `force: true`. (default: false) |
| `platform` | Only link if this variable matches python's `sys.platform` case insensitively. Preceed with '!' to exclude this platform instead. Note: Please put value in quotes if you include '!' so that yaml will parse correctly. |
| `environment` | Only link if this environmental variable exists and matches. Preceed with '!' to exclude variable matches instead. Note: Please put value in quotes if you include '!' so that yaml will parse correctly. |

## Complete Example as Dictionary

```yaml
- crossplatform-link:
    # Linux Only
    ~/.config/:
      platform: linux
      path: config/**
    # Windows only
    ~/.config-win/:
      platform: win32
      path: config-win/**
      fallback_to_copy: true
      force: true
    # Everything but windows
    ~/.config-all/:
      platform: '!win32'
      path: config/**
    # ONLY WSL
    ~/.bashrc/:
      environment: WSL_DISTRO_NAME # Optional
      path: .bashrc
    # ONLY WSL-Ubuntu
    ~/.profile/:
      environment: WSL_DISTRO_NAME=Ubuntu # Optional
      path: .profile
    # Everything but WSL-Ubuntu
    ~/.profile2/:
      environment: '!WSL_DISTRO_NAME=Ubuntu' # Optional
      path: .profile2
```

## Complete Example as List

```yaml
- crossplatform-link:
    # Windows only
    - ~/.config/:
      platform: win32
      path: config-win/**
      fallback_to_copy: true
      force: true
    # Everything but windows
    - ~/.config/:
      platform: '!win32'
      path: config/**
```

