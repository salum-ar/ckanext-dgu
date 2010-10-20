from ckan import model
from ckan.tests import *
from ckan.tests.wsgi_ckanclient import WsgiCkanClient
from ckan.lib.create_test_data import CreateTestData

from ckanext.dgu.scripts import mass_changer

class TestMassChanger(TestController):
    @classmethod
    def setup_class(self):
        # create test data
        model.notifier.initialise()
        self.tsi = TestSearchIndexer()
        CreateTestData.create()
        self.tsi.index()

        username = 'annafan'
        user = model.User.by_name(unicode(username))
        assert user
        self.testclient = WsgiCkanClient(self.app, api_key=user.apikey, base_location='/api/2')

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    def test_0_change_pkg(self):
        anna_before = self.anna.as_dict()
        war_before = self.war.as_dict()
        self.assert_equal(anna_before['license_id'], 'other-open')
        self.assert_equal(war_before['license_id'], None)

        # do the change
        new_license_id = 'test-license'        
        instructions = [
            mass_changer.ChangeInstruction('name', 'annakarenina',
                                           'license_id', new_license_id)]
        self.mass_changer = mass_changer.MassChanger(self.testclient, instructions)
        self.mass_changer.run()

        # check anna has new license
        pkg = model.Package.by_name(u'annakarenina')
        anna_after = self.anna.as_dict()
        war_after = self.war.as_dict()
        self.assert_equal(anna_after['license_id'], new_license_id)
        self.assert_equal(war_after['license_id'], war_before['license_id'])

        # check no other properties have changed
        for pkg_dict_before, pkg_dict_after in [(anna_before, anna_after),
                                                (war_before, war_after)]:
            keys = set(pkg_dict_before.keys())
            assert keys == set(pkg_dict_after.keys()), set(pkg_dict_after.keys()) ^ set(pkg_dict_before.keys())
            for key in keys:
                if key not in ['license_id', 'license', 'revision_id']:
                    assert pkg_dict_before[key] == pkg_dict_after[key], \
                           '%s %s: %r!=%r' % (pkg_dict_before['name'], key, pkg_dict_before[key], pkg_dict_after[key])

    def test_1_multiple_instructions(self):
        extra_field = 'genre'
        anna_before = self.anna.as_dict()
        war_before = self.war.as_dict()
        self.assert_equal(anna_before['extras'][extra_field], 'romantic novel')
        assert not war_before['extras'].has_key(extra_field)

        # do the change
        new_anna_value = 'test-anna' 
        new_value = 'test'
        instructions = [
            mass_changer.ChangeInstruction('genre', 'romantic novel',
                                           extra_field, new_anna_value),
            mass_changer.ChangeInstruction('*', '',
                                           extra_field, new_value)
            ]
        self.mass_changer = mass_changer.MassChanger(self.testclient, instructions)
        self.mass_changer.run()

        # check new licenses
        pkg = model.Package.by_name(u'annakarenina')
        anna_after = self.anna.as_dict()
        war_after = self.war.as_dict()
        self.assert_equal(anna_after['extras'][extra_field], new_anna_value)
        self.assert_equal(war_after['extras'][extra_field], new_value)
