[![Tests](https://github.com/fjelltopp/ckanext-spectrum/workflows/Tests/badge.svg?branch=master)](https://github.com/fjelltopp/ckanext-spectrum/actions)

# ckanext-spectrum

Provides tailored styling and features for CKAN, according to Avenir Health's requirements for their Spectrum CKAN instance.

For further information please see our other docs:

- [Spectrum CKAN API Documentation](https://documenter.getpostman.com/view/15920939/UzBpK5q9)


## Key features

The following key features are provided by this extension:

- Tailored UI styling, according to the Avenir Health branding.
- Integration with Giftless and CKAN extensions ckanext-blob-storage, ckanext-authz-service and ckanext-versions for revisioning and release management
- Template changes to streamline the UI to Avenir's needs.
- Changes to CKAN auth, to enable all users to be members of one organisation, but only edit their own datasets or the datasets they are collaborators on. The reason for this change is that the ckanext-blob-storage and ckanext-authz-service extensions are tightly coupled with the organisation model.



## Installation

To install ckanext-spectrum:

1. Activate your CKAN virtual environment, for example:

     . /usr/lib/ckan/default/bin/activate

2. Clone the source and install it on the virtualenv

    git clone https://github.com/fjelltopp/ckanext-spectrum.git
    cd ckanext-spectrum
    pip install -e .
	pip install -r requirements.txt

3. Add `spectrum` to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/ckan.ini`).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

     sudo service apache2 reload


## Developer installation

To install ckanext-spectrum for development, activate your CKAN virtualenv and
do:

    git clone https://github.com/fjelltopp/ckanext-spectrum.git
    cd ckanext-spectrum
    python setup.py develop
    pip install -r dev-requirements.txt


## Tests

To run the tests, do:

    pytest --ckan-ini=test.ini


## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)
