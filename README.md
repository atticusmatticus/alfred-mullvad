Mullvad VPN control for Alfred
=========

Easily control [Mullvad VPN](https://mullvad.net) with [Alfred](http://www.alfredapp.com).

![Mullvad for Alfred Screenshot](https://raw.github.com/atticusmatticus/alfred-mullvad/master/screenshot.gif)


## Features

- Script filter and ```vpn``` with support for the following commands:
    - ```doctor```, ```info```, ```install```, ```list```, ```search```, ```uninstall```, ```update``` and ```upgrade```
- Background cache refresh


## Installation

Download the [latest release](https://github.com/fniephaus/alfred-homebrew/releases/latest) and double click on the .alfredworkflow file, or use [packal](http://www.packal.org/workflow/homebrew-and-cask-alfred).


## Configuration

If you installed Homebrew Cask and changed where the applications are installed by adding a line like this to your `.bash_profile` or `.zshenv`:

```shell
# Specify your defaults in this environment variable
export HOMEBREW_CASK_OPTS="--appdir=/Applications"
```

You need to update workflow's settings accordingly to your configuration.

![Alfred Homebrew Configuration](https://raw.githubusercontent.com/fniephaus/alfred-homebrew/master/cask-config.png)

## Credits

This workflow uses [Github Octicons](https://github.com/github/octicons/) and [alfred-workflow](https://github.com/deanishe/alfred-workflow).
