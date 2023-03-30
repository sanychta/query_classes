import tacticenv
import time
import re
from tactic_server_stub import TACTIC
from pyasm.search import Search
from pyasm.security import Batch
from pyasm.command import Command
from tactic_server_stub import TacticServerStub


def time_it(start_time=None, message='Code flow running time:'):
    if start_time:
        print('{0} {1}'.format(message, time.time() - start_time))
    else:
        return time.time()
    
NO_IMAGE = '/assets/no_image.png'
NO_FILE_NAME = 'no_image.png'
PROJECT_NAME = 'dolly3d'
RESOURCE = {
    'logins' : {
        'resource': 'sthpw/login',
        'project': ''
    },
    'categories' : {
        'resource': 'complex/assets_category',
        'project': PROJECT_NAME
    },
    'assets': {
        'resource': 'dolly3d/assets',
        'project': PROJECT_NAME
    },
    'login_group': {
        'resource': 'sthpw/login_group',
        'project': PROJECT_NAME
    },
    'login_in_group': {
        'resource': 'sthpw/login_in_group',
        'project': PROJECT_NAME
    },
    'tasks': {
        'resource': 'sthpw/task',
        'project': PROJECT_NAME
    },
    'scenes': {
        'resource': 'complex/scenes',
        'project': PROJECT_NAME
    },
    'durations': {
        'resource': 'durations',
        'project': PROJECT_NAME
    },
    'notes': {
        'resource': 'sthpw/note',
        'project': PROJECT_NAME
    }
}

def match_resource(resource):
    """Function matching resources of URL of data provider with tactic search types

    :param
        resource: contains a synonym of the table
    :return
        dict: dictionary in the form of:
            search_type - table name.
            project - project name.
    """

    if resource[-1] == "/":
        resource = resource.replace('/', '')

    if resource in RESOURCE:
        r, p = RESOURCE.get(resource).values()
        return {'search_type': r, 'project': p}
    else:
        return {'search_type': resource, 'project': ''}


def get_file_url(s_type, s_code):
    """
    A function that returns the file name and url of the file

    :param s_type:
        contains search_type

    :param s_code:
        contains search_code

    :return:
        url of file and file name

    """
    file_url = NO_IMAGE
    file_name = NO_FILE_NAME
    server = TACTIC.get()
    splitted = s_type.split('&')
    if len(splitted) > 1:
        search_type = splitted[0]
    else:
        search_type = splitted[0].split('?')[0]
    filters = [('search_type', search_type), ('search_code', s_code)]
    s_object = server.query_snapshots(filters=filters, include_files=True, include_web_paths_dict=True)
    if s_object:
        to_dict = s_object[0]
        if to_dict.get('__web_paths_dict__'):
            web_paths_dict = to_dict.get('__web_paths_dict__')
            if web_paths_dict.get('web'):
                if len(web_paths_dict.get('web')) > 0:
                    file_url = web_paths_dict.get('web')[0]
                    file_name = web_paths_dict.get('web')[0].split('/')[-1]
                else:
                    file_url = NO_IMAGE
                    file_name = NO_FILE_NAME
    return {'url': file_url, 'name': file_name}

def get_images_urls(episodes_dict, search_keys):

    filters = {}
    for search_key in search_keys:
        if search_key.find('&') != -1:
            search_type, code = search_key.split('&')
        else:
            search_type, code = search_key.split('?')

        code = code.split('=')
        assert len(code) == 2
        code = code[1]
        
        filters.setdefault(search_type, []).append(code)

    for filter in filters:
        search_type = filter
        search_codes = filters.get(filter)
    filters = [('search_type', search_type), ('search_code', 'in', search_codes), ('is_latest', True), ('process', 'not in', ['render', 'cache'])]

    server = TACTIC.get()
    s_objects = server.query_snapshots(filters=filters, include_web_paths_dict=True)

    images_data = {}
    for code in search_codes:
        for s_object in s_objects:
            if s_object.get('search_code') == code:
                images_data.setdefault(code, []).append(
                    s_object.get('__web_paths_dict__'))
            else:
                images_data.setdefault(code, [])

    for episode in episodes_dict:
        code = episode.get('code')
        if images_data:
            for key, values in images_data.items():
                if key == code:
                    if values:
                        for value in values:
                            if value.get('web'):
                                url = value.get('web')[0]
                                file_name = url.split('/')[-1]
                                episode['image'] = {'url': url, 'name': file_name}
                            else:
                                episode['image'] = {'url': NO_IMAGE, 'name': NO_FILE_NAME}
                    else:
                        episode['image'] = {'url': NO_IMAGE, 'name': NO_FILE_NAME}
        else:
            episode['image'] = {'url': NO_IMAGE, 'name': NO_FILE_NAME}
    return episodes_dict


def get_duration():

    server = TacticServerStub()
    server.set_project('dolly3d')

    result = server.get_config_definition('complex/scenes', 'edit_definition', 'duration')
    result = result[result.find('<values>') + 8:result.find('</values>')]
    result = result.split('|')

    out = []
    for item in result:
        out.append({'duration': item})
    result = {
        'data': out,
        'total': len(out)
    }
    return result


def get_pipeline(project=None, args=None, mode=None):
    """
        project: name of project
        args: List of Dict {field, [values]}
        mode: 'or' or 'and' search mode
    """
    server = TacticServerStub()
    server.set_project(project)

    if args:
        search_list = []
        for arg in args:
            for field, value in arg.items():
                if isinstance(value, list):
                    value = '|'.join(value)
                search_list.append(f"['{field}', 'in', '{value}']")
        search_string = "".join(search_list)
        if mode:
            search_string += f"['{mode}']"
        return server.eval(f"@SOBJECT(sthpw/pipeline{search_string})")
    else:
        return server.eval("@SOBJECT(sthpw/pipeline)")


def get_pipeline_process_info(code, search_key=None, project=None):
    from pyasm.search import Search
    from pyasm.security import Batch

    Batch(project)

    if code is None or code == 'undefined':
        return []

    process_info = []
    if isinstance(code, list):
        code = '|'.join(code)
        expr = f"@SOBJECT(sthpw/pipeline['code', 'in', '{code}'])"
    else:
        expr = f"@SOBJECT(sthpw/pipeline['code', '{code}'])"

    pipe_object = Search.eval(expr)
    results = []
    if len(pipe_object) != 0:
        for item in pipe_object:
            for sub_item in item.get_processes():
                results.append(sub_item)
    else:
        return None
    if len(results) != 0:
        for item in results:
            process_info.append(item.get_attributes())
    return process_info


def parse_filter(data):

    fields = data[0].get('field').split('$')
    values = '&'.join(data[0].get('value')).split('|')
    out = []
    code_list = []
    field = 'code|AND'
    op = 'in'

    if len(fields) == 3:
        value_for_durations = values[2].split('&')
        if value_for_durations.count('') > 0:
            value_for_durations.remove('')

        values_proc = "|".join(values[0].split('&'))
        values_stat = "|".join(values[1].split('&'))
        Batch('dolly3d')
        s_object = Search.eval(f"@SOBJECT(sthpw/task['process', 'in', '{values_proc}']"
                               f"['status', 'in', '{values_stat}'].complex/scenes)")

        for result in s_object:
            code_list.append(result.get_code())

        out.append({"field": field, "operator": op, "value": code_list})
        out.append(
            {"field": fields[2], "operator": op, "value": value_for_durations})
    elif len(fields) == 2:
        if fields[0] == "PROC" and fields[1] == "STAT":
            values_proc = "|".join(values[0].split('&'))
            values_stat = "|".join(values[1].split('&'))
            Batch('dolly3d')
            s_object = Search.eval(f"@SOBJECT(sthpw/task['process', 'in', '{values_proc}']"
                                   f"['status', 'in', '{values_stat}'].complex/scenes)")
            for result in s_object:
                code_list.append(result.get_code())
            out.append({"field": field, "operator": op, "value": code_list})
        elif fields[0] == "PROC" and fields[1] != "STAT":
            value_for_durations = values[1].split('&')
            if value_for_durations.count('') > 0:
                value_for_durations.remove('')
            values_proc = "|".join(values[0].split('&'))
            Batch('dolly3d')
            s_object = Search.eval(
                f"@SOBJECT(sthpw/task['process', 'in', '{values_proc}'].complex/scenes)")
            for result in s_object:
                code_list.append(result.get_code())
            out.append({"field": field, "operator": op, "value": code_list})
            out.append(
                {"field": fields[1], "operator": op, "value": value_for_durations})
        elif fields[0] == "STAT" and fields[1] != "PROC":
            value_for_durations = values[1].split('&')
            if value_for_durations.count('') > 0:
                value_for_durations.remove('')
            values_stat = "|".join(values[0].split('&'))
            Batch('dolly3d')
            s_object = Search.eval(
                f"@SOBJECT(sthpw/task['status', 'in', '{values_stat}'].complex/scenes)")
            for result in s_object:
                code_list.append(result.get_code())
            out.append({"field": field, "operator": op, "value": code_list})
            out.append(
                {"field": fields[1], "operator": op, "value": value_for_durations})
    elif len(fields) == 1:
        if fields[0] == "PROC":
            values_proc = "|".join(values[0].split('&'))
            Batch('dolly3d')
            s_object = Search.eval(
                f"@SOBJECT(sthpw/task['process', 'in', '{values_proc}'].complex/scenes)")
            for result in s_object:
                code_list.append(result.get_code())
            out.append({"field": field, "operator": op, "value": code_list})
        else:
            values_stat = "|".join(values[0].split('&'))
            Batch('dolly3d')
            s_object = Search.eval(
                f"@SOBJECT(sthpw/task['status', 'in', '{values_stat}'].complex/scenes)")
            for result in s_object:
                code_list.append(result.get_code())
            out.append({"field": field, "operator": op, "value": code_list})

    return out


def add_assets_in_scenes(scene_code):
    Batch('dolly3d')
    assets = Search.eval(
        f"@SOBJECT(dolly3d/assets_in_scenes['scenes_code', '=', '{scene_code}'])")
    if assets == []:
        return '0/0'
    assets_code = []
    for asset in assets:
        assets_code.append(asset.get('assets_code'))
    assets_code = list(set(assets_code))
    code = "|".join(assets_code)
    complete_assets = Search.eval(
        f"@SOBJECT(sthpw/task['search_code', 'in', '{code}']['status', 'in', 'Опубликован|publish'])")

    return f'{len(complete_assets)}/{len(assets_code)}'


def get_assets_per_scenes(episodes_dict, episodes_codes):

    server = TACTIC.get()
    server.set_project('dolly3d')
    assets = server.eval(
        "@SOBJECT(dolly3d/assets_in_scenes['scenes_code', 'in', '{0}'])".format('|'.join(episodes_codes)))

    if assets == []:
        for episode in episodes_dict:
            code = episode.get('code')
            episode['assets'] = '0/0'
        return episodes_dict

    assets_per_episodes_all = {}
    for episode in episodes_codes:
        for asset in assets:
            if episode == asset['scenes_code']:
                assets_per_episodes_all.setdefault(
                    episode, set()).add(asset.get('assets_code'))
            else:
                assets_per_episodes_all.setdefault(episode, set())

    assets_code = []
    for asset in assets:
        assets_code.append(asset.get('assets_code'))
    code = "|".join(assets_code)
    complete_assets = server.eval(
        f"@SOBJECT(sthpw/task['search_code', 'in', '{code}']['status', 'in', 'Опубликован|publish'])")

    assets_per_episode = {}
    for episode in episodes_codes:
        for complete_asset in complete_assets:
            for asset in assets:
                if asset['assets_code'] == complete_asset['search_code']:
                    if episode == asset['scenes_code']:
                        assets_per_episode.setdefault(episode, set()).add(
                            complete_asset.get('search_code'))
                    else:
                        assets_per_episode.setdefault(episode, set())

    for episode in episodes_dict:
        code = episode.get('code')
        episode['assets'] = f'{len(assets_per_episode[code])}/{len(assets_per_episodes_all[code])}'

    return episodes_dict


def search_links(description):
    urls = re.compile(
        r"((https?):((//)|(\\\\))+[\w\d:#@%/;!$()~_?\+-=\\\.&]*)", re.MULTILINE | re.UNICODE)
    if re.search(urls.pattern, description):
        value = urls.sub(r'|\1', description)
        return value.split('|')
    else:
        return description


def parse_descriptions(data):
    if isinstance(data, list):
        for rec in data:
            if rec.get('description'):
                rec['description'] = search_links(rec.get('description'))
    else:
        if data.get('description'):
            data['description'] = search_links(data['description'])

def parse_keywords(data):
    if isinstance(data, list):
        for rec in data:
            if rec.get('keywords'):
                rec['keywords'] = re.split(',|;| |\n',rec.get('keywords'))
    else:
        if data.get('keywords'):
            data['keywords'] = list(filter(None, re.split(',|;| |\n', data.get('keywords'))))


class CreateQuery(Command):

    def __init__(self, resource, args):
        """
        :param resource: string: Contains a synonym of a table in the database
        :param args: dict: Dictionary with data to add to the database
        """
        self.resource = resource
        self.args = args
        super(CreateQuery, self).__init__()

    def execute(self):

        server = TacticServerStub()
        resource = match_resource(self.resource)
        server.set_project(resource['project'])
        code = ''
        search_type = ''
        trigger = False
        parent_key = None

        # Temporarily delete a field 'image' from args
        image_data = {}
        if 'image' in self.args:
            image_data = self.args['image']
            del self.args['image']

        if self.args.get('add_data'):
            add_data = self.args.get('add_data')
            trigger = bool(add_data.get('triggers'))
            if add_data.get('search_type'):
                search_type = add_data.get('search_type')

            if add_data.get('project'):
                project_code = add_data.get('project')
                server.set_project(project_code)

            if add_data.get('code'):
                code = add_data.get('code')

            if add_data.get('make_key'):
                parent_key = server.build_search_key(search_type=search_type,code=code,project_code=project_code)
            else:
                parent_key = None
            if search_type:
                search_type = server.build_search_type(search_type=search_type, project_code=project_code)

            del self.args['add_data']

        if resource['search_type'] == 'sthpw/task':
            self.args['search_code'] = code
            self.args['search_type'] = search_type
        result = server.insert(resource['search_type'], data=self.args, parent_key=parent_key, triggers=trigger)

        if isinstance(image_data, dict):
            if (image_data.get('url')):
                s_key = result.get('__search_key__')
                file_path = image_data.get('url').split('\n')[0]
                server.simple_checkin(search_key=s_key, context='icon', file_path=file_path, mode='uploaded')

        return {'data': result}


class CreateManyQuery(Command):

    def __init__(self, resource, variables):
        """
        :param resource: string: The type of search
        :param variables: dict: Dictionary
        """
        super(CreateManyQuery, self).__init__()
        self.resource = resource
        self.variables = variables

    def execute(self):
        server = TacticServerStub()
        resource = match_resource(self.resource)
        server.set_project(resource['project'])

        data = []

        # Temporarily delete a field 'image' from args
        for var in self.variables:
            if 'image' in var:
                del var['image']
            data.append(var)

        result = server.insert_multiple(search_type=resource['search_type'], data=data)

        return {'data': result}


class UpdateQuery(Command):

    def __init__(self, resource, id, args):
        """
        :param resource: string: The type of search
        :param id: string: ID
        :param args: dict: Dictionary
        """
        super(UpdateQuery, self).__init__()
        self.resource = resource
        self.id = id
        self.args = args

    def execute(self):
        server = TacticServerStub()
        resource = match_resource(self.resource)

        trigger = ''
        tmp_args = {}
        for fld, value in self.args.items():
            # if value not in [None, '']:
            #     tmp_args[fld] = value
            if value is None or value == '':
                pass
            else:
                tmp_args[fld] = value
        self.args = tmp_args

        # Temporarily delete a field 'image' from args
        if 'image' in self.args:
            del self.args['image']
        if 'triggers' in self.args:
            trigger = self.args['triggers']
            del self.args['triggers']

        search_key = server.build_search_key(
            resource['search_type'],
            code=self.id,
            column='id',
            project_code=resource['project'])

        result = server.update(search_key=search_key, data=self.args, triggers=trigger)

        return {'data': dict(result)}


class UpdateManyQuery(Command):

    def __init__(self, resource, ids, variables):
        """
        :param resource: string: The type of search
        :param ids: string: IDs
        :param variables: dict: Dictionary
        """
        super(UpdateManyQuery, self).__init__()
        self.resource = resource
        self.ids = ids
        self.variables = variables

    def execute(self):

        server = TacticServerStub()
        resource = match_resource(self.resource)

        data = {}
        count = 0
        for id_val in self.ids:
            s_key = server.build_search_key(
                search_type=resource['search_type'],
                project_code=resource['project'],
                column='id',
                code=id_val
            )
            data[s_key] = self.variables[count]
            count += 1

        result = server.update_multiple(data=data)

        return {'data': result}


class GetListQuery(Command):

    def __init__(self,
                 resource,
                 filters,
                 limit=0,
                 offset=0,
                 order_bys={'order_bys': 'id', 'ord_direction': 'asc'}
                 ):
        """
        :param resource: string
        :param filters: dict
        :param limit: integer
        :param offset: integer
        :param order_bys: dict
        """
        super(GetListQuery, self).__init__()
        self.limit = limit
        self.offset = offset
        self.ord_field = order_bys['order_bys']
        self.ord_direction = order_bys['ord_direction']
        self.filters = filters
        self.resource = resource

    @staticmethod
    def get_filter(data):
        """
        data: list
        """
        out = []
        if len(data) > 0:
            if data[0].get('field') == 'assets_category_code|AND':
                data.reverse()

            t_data = []
            counter = 0
            for f in data:
                if f.get('field').find('PROC') >=0 or f.get('field').find('STAT') >= 0:
                    t_data = parse_filter([f])
                    data.pop(counter)
                counter+=1
            for t in t_data:
                data.append(t)

            if data:
                for rec in data:
                    oper = rec.get('operator')
                    values = rec.get('value')

                    if values == [None]:
                        return None

                    fields = rec.get('field').split('|')
                    if oper in ['contains', 'startswith', 'startsWith', 'starts with',
                                'starts With', 'endswith', 'endsWith', 'ends with', 'ends With']:
                        oper = 'EQI'
                    elif oper == 'null':
                        oper = '='
                        values = None
                    elif oper == 'nnull':
                        oper = '!='
                        values = ''
                    elif oper == ['isAnyOf', 'in']:
                        oper = 'in'
                    elif oper == 'eq':
                        oper = '='

                    for field in fields:
                        if field == '' or field is None:
                            pass
                        else:
                            if field == 'AND':
                                out[-1]['method'] = 'and'
                            else:
                                out.append({'field': field, 'value': values, 'op': oper, 'method': 'or'})
                return out
            else:
                return None

    def execute(self):
        main_time = time_it()
        resource = match_resource(self.resource)

        if resource['search_type'] == 'pipes':
            if len(self.filters) > 0:
                code = self.filters[0].get('value')
            else:
                result = {'data': 0,
                          'total': 0}
                return result

            data = get_pipeline_process_info(code=code, project='dolly3d')
            result = {'data': data,
                      'total': len(data)}
            return result

        if resource['search_type'] == 'durations':
            return get_duration()


        Batch(resource['project'])
        s_object = Search(resource['search_type'])

        s_filter = self.get_filter(self.filters)

        if s_filter is not None:

            for filter_val in s_filter:
                name = filter_val.get('field')
                value = filter_val.get('value')
                op = filter_val.get('op')
                fl = (name, op, value)

                if op == 'EQI':
                    s_object.add_op_filters([fl])
                else:
                    s_object.add_filter(name=name, value=value, op=op)
                if filter_val.get('method') == 'and':
                    s_object.add_op('and')
                else:
                    s_object.add_op('or')

        count = s_object.get_count()

        s_object.add_order_by(self.ord_field, self.ord_direction)
        if self.limit != 0:
            s_object.set_limit(self.limit)
            s_object.set_offset(self.offset)
        s_result = s_object.get_sobjects()
        
        episodes_codes = []
        output = []
        search_keys = []

        for result in s_result:
            out_dict = result.get_sobject_dict()

            if out_dict.get('__search_key__'):
                search_keys.append(out_dict.get('__search_key__'))

            if resource['search_type'] == 'complex/scenes':
                episodes_codes.append(result.get_code())
            output.append(out_dict)
        
        if search_keys:
            output = get_images_urls(output, search_keys)

        if resource['search_type'] == 'complex/scenes':
            output = get_assets_per_scenes(output, episodes_codes)

        # unique_els = []
        # for dict_item in output:
        #     if dict_item not in unique_els:
        #         unique_els.append(dict_item)
        # output = unique_els

        # parse_descriptions(output)

        result = {'data': output,
                  'total': count}
        time_it(main_time, f'Time of loading resource {resource["search_type"]}:    ')
        return result


class GetManyQuery(Command):

    def __init__(self, resource, ids):
        super(GetManyQuery, self).__init__()
        self.resource = resource
        self.ids = ids

    def execute(self):
        resource = match_resource(self.resource)
        Batch(resource['project'])
        s_search = Search(resource['search_type'])
        s_search.add_filters('id', self.ids)
        result = s_search.get_sobjects()

        output = []
        for row in result:
            output.append(row.get_sobject_dict())

        return {'data': output}


class GetOneQuery(Command):

    def __init__(self, resource, id):
        super(GetOneQuery, self).__init__()
        self.resource = resource
        self.id = id

    def execute(self):
        result = {}
        resource = match_resource(self.resource)
        server = TacticServerStub()
        server.set_project(resource['project'])
        results = server.query(search_type=resource['search_type'], filters=[('id', '=', int(self.id))])

        if len(results) > 0:
            result = results[0]

        if self.resource == 'assets':
            s_key = server.build_search_key(search_type='complex/assets_category',
                                            code=result.get('assets_category_code'),
                                            project_code=resource['project'])
            a_result = server.get_by_search_key(s_key)
            result['assets_category'] = a_result
        if resource['search_type'] == 'complex/scenes':
            result['assets'] = add_assets_in_scenes(result.get('code'))
        
        result['image'] = get_file_url(result['__search_key__'], result['code'])

        parse_descriptions(result)
        parse_keywords(result)

        return {'data': result}


class DeleteOneQuery(Command):

    def __init__(self, resource, id, variables):
        """

        :param resource: string resource
        :param id: integer
        :param variables: dict of variables
        """
        super(DeleteOneQuery, self).__init__()
        self.resource = resource
        self.id = id
        self.variables = variables

    def execute(self):

        resource = match_resource(self.resource)

        server = TacticServerStub()

        server.set_project(resource['project'])

        search_key = server.build_search_key(search_type=resource['search_type'], code=self.id, column='id')

        if self.variables.get('retired'):
            results = server.retire_sobject(search_key=search_key)
        else:
            results = server.delete_sobject(search_key=search_key)

        return {'data': results}


class DeleteManyQuery(Command):

    def __init__(self, resource, ids, variables=None):
        """

        :param resource: string resource
        :param ids: list of integer ids
        :param variables: dict of variables
        """
        super(DeleteManyQuery, self).__init__()
        self.resource = resource
        self.ids = ids
        self.variables = variables

    def execute(self):

        result = []

        resource = match_resource(self.resource)

        server = TacticServerStub()

        server.set_project(resource['project'])

        if self.variables.get('retired'):
            for id_val in self.ids:
                search_key = server.build_search_key(search_type=resource['search_type'], code=id_val, column='id')
                result.append(server.retire_sobject(search_key=search_key))
        else:
            for id_val in self.ids:
                search_key = server.build_search_key(search_type=resource['search_type'], code=id_val, column='id')
                result.append(server.delete_sobject(search_key=search_key))

        return {'data': result}


class CheckUploadedFile(Command):

    def __init__(self, data):
        """
        Upload the file
        :param data: dict with file name and path
            data contains:
                search_type - contains a synonym of the table being accessed before
                    being converted by the match_resource function
                file_path - contains the full path and file name, after uploading to the temporary folder of the server
                code - asset ID
        """
        super(CheckUploadedFile, self).__init__()
        self.data = data

    def execute(self):
        print(f'DATA:\n{self.data}\n')
        search_type = self.data.get('search_type')
        file = self.data.get('file_path').split('\n')[0]
        resource = match_resource(search_type)

        server = TacticServerStub()

        server.set_project(resource['project'])

        if self.data.get('code') in ['undefined', '', None]:
            file_url = NO_IMAGE
            file_name = NO_FILE_NAME
            return {'url': file_url, 'name': file_name}

        search_key = server.build_search_key(
            search_type=resource['search_type'],
            code=self.data.get('code'),
            project_code=resource['project'],
        )

        result = server.simple_checkin(search_key=search_key, context='icon', file_path=file, mode='uploaded')

        file_url = NO_IMAGE
        file_name = NO_FILE_NAME

        filters = [('code', result.get('code'))]
        s_object = server.query_snapshots(filters=filters, include_files=True, include_web_paths_dict=True)
        print(f'\n{s_object}\n')
        if s_object:
            data = s_object[0]
        else:
            file_url = NO_IMAGE
            file_name = NO_FILE_NAME
            return {'url': file_url, 'name': file_name}

        if data.get('__web_paths_dict__'):
            web_paths_dict = data.get('__web_paths_dict__')
            if web_paths_dict.get('web'):
                if len(web_paths_dict.get('web')) > 0:
                    file_url = web_paths_dict.get('web')[0]
                    file_name = web_paths_dict.get('web')[0].split('/')[-1]
                else:
                    file_url = NO_IMAGE
                    file_name = NO_FILE_NAME

        return {'url': file_url, 'name': file_name}


class GetUserInfo(Command):

    def __init__(self, data):
        """
        Upload the file
        :param data: dict with file name and path
            data contains:
                search_type - contains a synonym of the table being accessed before
                    being converted by the match_resource function
                ticket - current login ticket
        """
        super(GetUserInfo, self).__init__()
        self.data = data

    def execute(self):

        search_type = self.data.get('resource')
        ticket = self.data.get('ticket')
        resource = match_resource(search_type)
        server = TacticServerStub()

        search_type = resource['search_type']
        user_code = ''
        result = server.query(search_type, [('ticket', ticket)])
        if len(result) > 0:
            user_code = result[0].get('login')

        result = server.query('sthpw/login', [("code", user_code)])
        if len(result) > 0:
            result = result[0]

        user_info = {
            "code": result.get("code"),
            "login": result.get("display_name"),
            "name": result.get("login"),
            "phone_number": result.get("phone_number"),
            "email": result.get("email"),
            "id": result.get("id"),
            "image": get_file_url('sthpw/login', result.get('code')),
            "ticket": server.get_login_ticket(),
        }

        if result.get('code') == 'admin':
            user_info['user_groups'] = 'admin'
        else:
            results = server.eval(f"@SOBJECT(sthpw/login_in_group['login', '{user_code}'])")
            user_groups = []
            if len(results) > 0:
                for result in results:
                    user_groups.append(result.get('login_group'))
            user_info['user_groups'] = '|'.join(user_groups)

        return user_info


if __name__ == "__main__":
    pass
