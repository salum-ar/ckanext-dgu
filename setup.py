from setuptools import setup, find_packages

version = '0.1'

setup(
    name='ckanext-dgu',
    version=version,
    long_description="""\
    """,
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.dgu'],
    include_package_data=True,
    zip_safe=False,
    author='Open Knowledge Foundation',
    author_email='info@okfn.org',
    license='AGPL',
    url='http://knowledgeforge.net/ckan/',
    description='CKAN DGU extensions',
    keywords='data packaging component tool server',
    install_requires=[
        'swiss',
        'ckanclient>=0.5',
        'xlrd>=0.7.1',
        'xlwt>=0.7.2',
        #'ckanext', when it is released
    ],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    package_data={'ckan': ['i18n/*/LC_MESSAGES/*.mo']},
    entry_points="""
        [ckan.plugins]
        dgu_routes=ckanext.dgu.forms:FormAPI
        
        [console_scripts]
        ons_loader = ckanext.dgu.ons:load
        cospread_loader = ckanext.dgu.cospread:load
        change_licenses = ckanext.dgu.scripts.change_licenses_cmd:command
        transfer_url = ckanext.dgu.scripts.transfer_url_cmd:command
        ons_analysis = ckanext.dgu.scripts.ons_analysis_cmd:command

        [ckan.forms]
        gov3 = ckanext.dgu.forms.package_gov3:get_gov3_fieldset
    """,
    test_suite = 'nose.collector',
)
