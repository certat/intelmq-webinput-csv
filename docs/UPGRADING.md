# Upgrade instructions

For installation instructions, see [INSTALL.md](INSTALL.md).

## Upgrade IntelMQ Webinput CSV

The upgrade depends on how you installed IntelMQ.

### Packages

Use your systems package management.

### PyPi

```
> pip install -U --no-deps intelmq_webinput_csv
```
Using `--no-deps` will not upgrade dependencies, which would probably overwrite the system's libraries.
Remove this option to also upgrade dependencies.

### Local repository

If you have an editable installation, refer to the instructions in the [Developers Guide](Developers-Guide.md#development-environment).

Update the repository depending on your setup (e.g. `git pull origin master`).

And run the installation again:
```bash
> pip install .
```
For editable installations, run `pip install -e .` instead.

## Check the installation

Go through [NEWS.md](../NEWS.md) and apply necessary adaptions to your setup.
If you have adapted IntelMQ's code, also read the [CHANGELOG.md](../CHANGELOG.md).
