from ckan import model
from ckan.lib.helpers import OrderedDict
from ckanext.dgu.lib.publisher import go_down_tree

import logging

log = logging.getLogger(__name__)

def sql_to_filter_by_organisation(organisation,
                                  include_sub_organisations=False):
    '''
    Returns: (sql_org_filter, sql_params)
    In your sql you need:
          WHERE %(org_filter)s
    Run this function:
          sql_org_filter, sql_params = sql_to_filter_by_organisation( ... )
    And execute your sql with the tuple:
          rows = model.Session.execute(sql % sql_org_filter, sql_params)
    '''
    sql_org_filter = {}
    sql_params = {}
    if not include_sub_organisations:
        sql_org_filter['org_filter'] = '"group".name = :org_name'
        sql_params['org_name'] = organisation.name
    else:
        sub_org_filters = ['"group".name=\'%s\'' % org.name for org in go_down_tree(organisation)]
        sql_org_filter['org_filter'] = '(%s)' % ' or '.join(sub_org_filters)
    return sql_org_filter, sql_params

def british_date_formatter(datetime_):
    return datetime_.strftime('%d/%m/%Y')

def british_datetime_formatter(datetime_):
    return datetime_.strftime('%d/%m/%Y  %M:%H')

def organisation_resources(organisation_name,
                           include_sub_organisations=False,
                           date_formatter=None):
    '''
    Returns a dictionary detailing resources for each dataset in the
    organisation specified.

    headings: ['Publisher title', 'Publisher name', 'Dataset title', 'Dataset name', 'Resource index', 'Description', 'URL', 'Format', 'Date created']

    i.e.:
    {'publisher_name': 'cabinet-office',
     'publisher_title:': 'Cabinet Office',
     'schema': {'Publisher title': 'publisher_id',
                'Publisher name': 'publisher_name',
                ...},
     'rows': [ row_dict, row_dict, ... ]
    }
    '''
    sql = """
        select package.id as package_id,
               package.title as package_title,
               package.name as package_name,
               resource.id as resource_id,
               resource.url as resource_url,
               resource.format as resource_format,
               resource.description as resource_description,
               resource.position as resource_position,
               resource.created as resource_created,
               "group".id as publisher_id,
               "group".name as publisher_name,
               "group".title as publisher_title
        from resource
            left join resource_group on resource.resource_group_id = resource_group.id
            left join package on resource_group.package_id = package.id
            left join member on member.table_id = package.id
            left join "group" on member.group_id = "group".id
        where
            package.state='active'
            and resource.state='active'
            and resource_group.state='active'
            and "group".state='active'
            and %(org_filter)s
        order by "group".name, package.name, resource.position
        """
    org = model.Group.by_name(organisation_name)
    if not org:
        abort(404, 'Publisher not found')
    organisation_title = org.title

    sql_org_filter, sql_params = sql_to_filter_by_organisation(
        org,
        include_sub_organisations=include_sub_organisations)
    raw_rows = model.Session.execute(sql % sql_org_filter, sql_params)

    schema = OrderedDict((('Publisher title', 'publisher_title'),
                          ('Publisher name', 'publisher_name'),
                          ('Dataset title', 'package_title'),
                          ('Dataset name', 'package_name'),
                          ('Resource index', 'resource_position'),
                          ('Resource ID', 'resource_id'),
                          ('Description', 'resource_description'),
                          ('URL', 'resource_url'),
                          ('Format', 'resource_format'),
                          ('Date created', 'resource_created'),
                          ))
    rows = []
    for raw_row in raw_rows:
        #row = [getattr(raw_row, key) for key in schema.values()]
        row = OrderedDict([(key, getattr(raw_row, key)) for key in schema.values()])
        if date_formatter:
            for col in ('resource_created',):
                if row[col]:
                    row[col] = date_formatter(row[col])
        rows.append(row)
    return {'publisher_name': org.name,
            'publisher_title': org.title,
            'schema': schema,
            'rows': rows,
            }

def organisation_dataset_scores(organisation_name,
                                include_sub_organisations=False):
    '''
    Returns a dictionary detailing openness scores for the organisation
    for each dataset.

    i.e.:
    {'publisher_name': 'cabinet-office',
     'publisher_title:': 'Cabinet Office',
     'data': [
       {'package_name', 'package_title', 'resource_url', 'openness_score', 'reason', 'last_updated', 'is_broken', 'format'}
      ...]

    NB the list does not contain datasets that have 0 resources and therefore
       score 0

    '''
    values = {}
    sql = """
        select package.id as package_id,
               task_status.key as task_status_key,
               task_status.value as task_status_value,
               task_status.error as task_status_error,
               task_status.last_updated as task_status_last_updated,
               resource.id as resource_id,
               resource.url as resource_url,
               resource.position,
               package.title as package_title,
               package.name as package_name,
               "group".id as publisher_id,
               "group".name as publisher_name,
               "group".title as publisher_title
        from resource
            left join task_status on task_status.entity_id = resource.id
            left join resource_group on resource.resource_group_id = resource_group.id
            left join package on resource_group.package_id = package.id
            left join member on member.table_id = package.id
            left join "group" on member.group_id = "group".id
        where
            entity_id in (select entity_id from task_status where task_status.task_type='qa')
            and package.state = 'active'
            and resource.state='active'
            and resource_group.state='active'
            and "group".state='active'
            and task_status.task_type='qa'
            and task_status.key='status'
            %(org_filter)s
        order by package.title, package.name, resource.position
        """
    sql_options = {}
    org = model.Group.by_name(organisation_name)
    if not org:
        abort(404, 'Publisher not found')
    organisation_title = org.title

    if not include_sub_organisations:
        sql_options['org_filter'] = 'and "group".name = :org_name'
        values['org_name'] = organisation_name
    else:
        sub_org_filters = ['"group".name=\'%s\'' % org.name for org in go_down_tree(org)]
        sql_options['org_filter'] = 'and (%s)' % ' or '.join(sub_org_filters)

    rows = model.Session.execute(sql % sql_options, values)
    data = dict() # dataset_name: {properties}
    for row in rows:
        package_data = data.get(row.package_name)
        if not package_data:
            package_data = OrderedDict((
                ('dataset_title', row.package_title),
                ('dataset_name', row.package_name),
                ('publisher_title', row.publisher_title),
                ('publisher_name', row.publisher_name),
                # the rest are placeholders to hold the details
                # of the highest scoring resource
                ('resource_position', None),
                ('resource_id', None),
                ('resource_url', None),
                ('openness_score', None),
                ('openness_score_reason', None),
                ('last_updated', None),
                ))
        if row.task_status_value > package_data['openness_score']:
            package_data['resource_position'] = row.position
            package_data['resource_id'] = row.resource_id
            package_data['resource_url'] = row.resource_url

            try:
                package_data.update(json.loads(row.task_status_error))
            except ValueError, e:
                log.error('QA status "error" should have been in JSON format, but found: "%s" %s', task_status_error, e)
                package_data['reason'] = 'Could not display reason due to a system error'

            package_data['openness_score'] = row.task_status_value
            package_data['openness_score_reason'] = package_data['reason'] # deprecated
            package_data['last_updated'] = row.task_status_last_updated

        data[row.package_name] = package_data

    # Sort the results by openness_score asc so we can see the worst
    # results first
    data = OrderedDict(sorted(data.iteritems(),
        key=lambda x: x[1]['openness_score']))

    return {'publisher_name': organisation_name,
            'publisher_title': organisation_title,
            'data': data.values()}


def feedback_report(publisher, include_sub_publishers=False, include_published=False, use_cache=False):
    """
    For the publisher provided (and optionally for sub-publishers) this
    function will generate a report on the feedback for that publisher.
    """
    import collections
    import datetime
    import ckan.lib.helpers as helpers
    from ckanext.dgu.lib.publisher import go_down_tree
    from ckanext.dgu.model.feedback import Feedback
    from operator import itemgetter
    from sqlalchemy.util import OrderedDict

    publisher_name = '__all__'
    if publisher:
        publisher_name = publisher.name

    if use_cache:
        key = 'feedback-report'
        if include_published:
          key = 'feedback-all-report'

        if include_sub_publishers:
            key = "".join([key, '-withsubpub'])
        cache = model.DataCache.get_fresh(publisher_name, key)
        if cache is None:
            log.info("Did not find cached report - %s/%s" % (publisher_name,key,))
        else:
            log.info("Found feedback report in cache")
            return cache

    if publisher:
        group_ids = [publisher.id]
        if include_sub_publishers:
            groups = sorted([x for x in go_down_tree(publisher)], key=lambda x: x.title)
            group_ids = [x.id for x in groups]

        memberships = model.Session.query(model.Member)\
            .join(model.Package, model.Package.id==model.Member.table_id)\
            .filter(model.Member.state == 'active')\
            .filter(model.Member.group_id.in_(group_ids))\
            .filter(model.Member.table_name == 'package')\
            .filter(model.Package.state == 'active')

    else:
        memberships = model.Session.query(model.Member)\
            .join(model.Package, model.Package.id==model.Member.table_id)\
            .filter(model.Member.state == 'active')\
            .filter(model.Member.table_name == 'package')\
            .filter(model.Package.state == 'active')

    results = []
    for member in memberships.all():
        pkg = model.Package.get(member.table_id)

        # For now we will skip over unpublished items
        if not include_published and not pkg.extras.get('unpublished', False):
            continue

        key = pkg.name

        data = collections.defaultdict(int)
        data['publisher-name'] = member.group.name
        data['generated-at'] = helpers.render_datetime(datetime.datetime.now(), "%d/%m/%Y %H:%M")
        data['publisher-title'] = member.group.title
        data['package-name'] = pkg.name
        data['package-title'] = pkg.title
        data['publish-date'] = pkg.extras.get('publish-date', '')

        for item in model.Session.query(Feedback).filter(Feedback.visible == True)\
                .filter(Feedback.package_id == member.table_id )\
                .filter(Feedback.active == True ):
            if item.economic: data['economic'] += 1
            if item.social: data['social'] += 1
            if item.linked: data['linked'] += 1
            if item.other: data['other'] += 1
            if item.effective: data['effective'] += 1

        data['total-comments'] = sum([data['economic'], data['social'],
                                     data['linked'], data['other'],
                                     data['effective']])
        results.append(data)

    return sorted(results, key=itemgetter('package-title'))



def cached_reports(reports_to_run=None):
    """
    This function is called by the ICachedReport plugin which will
    iterate over all if the reports that need to be run
    """
    import json
    from ckan.lib.json import DateTimeJsonEncoder

    local_reports = set(['feedback-report'])
    if reports_to_run:
      local_reports = set(reports_to_run) & local_reports

    if not local_reports:
      return

    log.info("Generating feedback report")

    if 'feedback-report' in local_reports:
      log.info("Generating feedback report for all publishers")
      val = feedback_report(None, use_cache=False)
      model.DataCache.set('__all__', "feedback-report", json.dumps(val))

      log.info("Generating feedback report for all publishers")
      val = feedback_report(None, use_cache=False, include_published=True)
      model.DataCache.set('__all__', "feedback-all-report", json.dumps(val))


    publishers = model.Session.query(model.Group).\
        filter(model.Group.type=='publisher').\
        filter(model.Group.state=='active').order_by('title')

    for publisher in publishers:
        # Run the feedback report with and without include_sub_organisations set
        if 'feedback-report' in local_reports:
          log.info("Generating unpublished feedback report for %s" % publisher.name)
          val = feedback_report(publisher, use_cache=False)
          model.DataCache.set(publisher.name, "feedback-report", json.dumps(val))

          log.info("Generating unpublished feedback report for %s and children" % publisher.name)
          val = feedback_report(publisher, include_sub_publishers=True, use_cache=False)
          model.DataCache.set(publisher.name, "feedback-report-withsubpub", json.dumps(val))

          log.info("Generating feedback report for %s" % publisher.name)
          val = feedback_report(publisher, include_published=True, use_cache=False)
          model.DataCache.set(publisher.name, "feedback-all-report", json.dumps(val))

          log.info("Generating feedback report for %s and children" % publisher.name)
          val = feedback_report(publisher, include_sub_publishers=True, include_published=True, use_cache=False)
          model.DataCache.set(publisher.name, "feedback-all-report-withsubpub", json.dumps(val))

          model.Session.commit()

