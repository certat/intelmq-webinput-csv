**Table of Contents**

1. [Requirements](#requirements)
2. [Install Dependencies](#install-dependencies)
   * [Ubuntu / Debian 8](#ubuntu---debian)
   * [openSUSE Leap 42.2](#opensuse-leap-422--423)
3. [Installation](#installation)
   * [Native packages](#native-packages)
   * [With pip](#with-pip)
     * [From PyPi](#from-pypi)
     * [From the repository](#from-the-repository)
4. [Afterwards](#afterwards)


Please report any errors you encounter at https://github.com/certat/intelmq-webinput-csv/issues

For upgrade instructions, see [UPGRADING.md](UPGRADING.md).

# Requirements

The following instructions assume the following requirements:

Supported and recommended operating systems are:
* Debian 8 and 9
* OpenSUSE Leap 42.2 and 42.3
* Ubuntu: 14.04 and 16.04 LTS

Other distributions which are (most probably) supported include CentOS, RHEL, Fedora and openSUSE Tumbleweed as long as [Flask](http://flask.pocoo.org/) is available.

You need an installed [intelmq](https://intelmq.org) installation on the same machine.

# Install Dependencies

If you are using native packages, you can simply skip this section as all dependencies are installed automatically.

## Ubuntu / Debian

```bash
apt-get install python3-flask
```

## openSUSE Leap 42.2 / 42.3

```bash
zypper install python3-Flask
```

# Installation

There are different methods to install IntelMQ:

* as native deb/rpm package
* from PyPi: to get the latest releases as python package
* from the (local) repository: for developers to get the latest (unstable!) version and/or have local modifications

## Native packages

Get the install instructions for your operating system here:
https://software.opensuse.org/download.html?project=home%3Asebix%3Aintelmq%3Acertat&package=intelmq-webinput-csv

Currently, these operating systems are supported by the packages:
* Debian 8 and 9
* Fedora 25
* openSUSE Leap 42.2 and 42.3
* openSUSE Tumbleweed
* Ubuntu 16.04

Please report any errors or improvements at https://github.com/certtools/intelmq/issues Thanks!

## With pip

Please note that the pip3 installation method does not (and cannot) create /opt/intelmq/etc/examples/webinput_csv.conf.
As workaround you need to move the file from the site-packages directory to /opt/intelmq manually.
The location of this directory varies, it could be `/usr/lib/python3.4/site-packages`, `/usr/local/lib/python3.5/dist-packages/` or similar.
For example:
```bash
mv /usr/lib/python3.4/site-packages/opt/intelmq /opt/
```

### From PyPi

```bash
sudo -s

pip3 install intelmq-webinput-csv
```

### From the repository

Clone the repository if not already done:
```bash
git clone https://github.com/certat/intelmq-webinput-csv.git /tmp/intelmq
cd /tmp/intelmq
```

If you have a local repository and you have or will do local modification, consider using an editable installation (`pip install -e .`).
```
sudo -s

pip3 install .
```

### Webserver configuration

Configure your server to use the intelmq_webinput_csv executable as WSGI script. A configuration snippet for Apache can be found in `contrib/apache/002_intelmq_webinput_csv.conf`.

# Afterwards

Now continue with the [User Guide](User-Guide.md).
