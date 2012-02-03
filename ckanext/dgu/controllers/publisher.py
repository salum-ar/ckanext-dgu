import logging
from urllib import urlencode

from sqlalchemy.orm import eagerload_all
from ckan.lib.base import BaseController, c, model, request, render, h, g
from ckan.lib.base import ValidationException, abort, gettext
from pylons.i18n import get_lang, _
import ckan.authz as authz
from ckan.lib.alphabet_paginate import AlphaPage
from ckan.lib.navl.dictization_functions import DataError, unflatten, validate
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import check_access, get_action
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckan.lib.dictization.model_dictize import package_dictize
from ckan.controllers.group import GroupController
import ckan.forms


log = logging.getLogger(__name__)

class PublisherController(GroupController):

    ## end hooks
    def index(self):

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}

        data_dict = {'all_fields': True}

        try:
            check_access('site_read', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))
        
        #results = [g for g in get_action('group_list')(context, data_dict) if g['type'] == 'publisher']
        
        # Testing junk until I can get the publisher new working again.
        results = []
        for x in range( 1, 25):
            results = results + [
                { "title": "ABC", "name": "alpha_beta_c", "packages": 1, "display_name": "ABC", "description": "A description"},
                { "title": "DEF", "name": "deaf",         "packages": 2, "display_name":  "DEF", "description": "A description"},
                { "title": "XYZ", "name": "xylophone",    "packages": 3, "display_name": "XYZ", "description": "A description" },                        
            ]

        c.page = AlphaPage(
            controller_name="ckanext.dgu.controllers.publisher:PublisherController",
            collection=results,
            page=request.params.get('page', 'A'),
            alpha_attribute='title',
            other_text=_('-'),
        )
        
        c.departments = [
                { "title": "ABC", "name": "alpha_beta_c", "packages": 1, "display_name": "ABC", "description": "A description"},
                { "title": "DEF", "name": "deaf",         "packages": 2, "display_name":  "DEF", "description": "A description"},
                { "title": "XYZ", "name": "xylophone",    "packages": 3, "display_name": "XYZ", "description": "A description" },                        
            ]
        
        return render('publishers/index.html')
