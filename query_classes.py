import tacticenv
import time
from tactic_server_stub import TACTIC
from pyasm.search import Search
from pyasm.security import Batch
from pyasm.command import Command
from tactic_server_stub import TacticServerStub
from collections import OrderedDict


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
        'project': ''
        # 'project': PROJECT_NAME
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


def match_resource(resource_name):
    """Function matching resources of URL of data provider with tactic search types

    :param
        resource: contains a synonym of the table
    :return
        dict: dictionary in the form of:
            search_type - table name.
            project - project name.
    """

    resource_name = resource_name.rstrip('/')

    if resource_name in RESOURCE:
        r, p = RESOURCE.get(resource_name).values()
        return {'search_type': r, 'project': p}
    else:
        return {'search_type': resource_name, 'project': ''}


def get_file_url(s_type, s_code):
    """
    This function takes two parameters, s_type and s_code, and returns a dictionary containing the url and name of a file.
    
    Parameters:
    s_type (str): The type of search to be performed.
    s_code (str): The code of the file to be searched for.
    
    Returns:
    dict: A dictionary containing the url and name of the file.
    """
    # Split the s_type parameter into two parts
    splitted = s_type.split('&')
    
    # If the length of the splitted list is 1, get the first element of the list and split it by '?'
    # Otherwise, get the first element of the list
    search_type = splitted[0].split('?')[0] if len(splitted) == 1 else splitted[0]

    # Query the TACTIC object for the file with the given search type and code
    s_object = TACTIC.get().query_snapshots(filters=[('search_type', search_type), ('search_code', s_code)], include_files=True, include_web_paths_dict=True)

    # If the object exists
    if s_object:
        # Get the web paths dictionary
        web_paths_dict = s_object[0].get('__web_paths_dict__', {}).get('web', [])
        # If the dictionary exists
        if web_paths_dict:
            # Return a dictionary containing the url and name of the file
            return {'url': web_paths_dict[0], 'name': web_paths_dict[0].split('/')[-1]}
    # If the object does not exist, return a dictionary containing the default url and name
    return {'url': NO_IMAGE, 'name': NO_FILE_NAME}


def get_images_urls(episodes_dict, search_keys):

    for s_type, s_code in search_keys.items():
        search_type = s_type
        search_codes = s_code
    filters = [('search_type', search_type), ('search_code', 'in', search_codes), ('is_latest', True), ('process', 'not in', ['render', 'cache'])]

    s_objects = TACTIC.get().query_snapshots(filters=filters, include_web_paths_dict=True)

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
    server = TACTIC.get()
    server.set_project(PROJECT_NAME)
    result = server.get_config_definition('complex/scenes', 'edit_definition', 'duration')
    out = [{'duration': item} for item in result[result.find('<values>') + 8:result.find('</values>')].split('|')]
    return {'data': out, 'total': len(out)}


def get_pipeline_process_info(code, search_key=None, project=None):
    from pyasm.search import Search
    from pyasm.security import Batch

    Batch(project)

    if code is None or code == 'undefined': return []

    if isinstance(code, list):
        expr = f"@SOBJECT(sthpw/pipeline['code', 'in', '{'|'.join(code)}'])"
    else:
        expr = f"@SOBJECT(sthpw/pipeline['code', '{code}'])"

    pipe_object = Search.eval(expr)
    return [sub_item.get_attributes() for item in pipe_object for sub_item in item.get_processes()]


def get_code_list(search_string, project=None):
    Batch(project)
    return [result.get_code() for result in Search.eval(search_string)] if search_string else []

def fill_filter_fields(field, operator, value):
    return {
        "field": field,
        "operator": operator,
        "value": value
    }

OPERATOR_IN = 'in'
FILTER_FIELD_CODE = 'code|AND'

def parse_filter(input_data):
    
    field_list = input_data.get('field').split('$')
    values = '&'.join(input_data.get('value')).split('|')
    new_filter_fields = []

    match len(field_list):
        case 3:
            duration_values = list(filter(None, values[2].split('&')))
            process_values = "|".join(values[0].split('&'))
            status_values = "|".join(values[1].split('&'))
            
            new_filter_fields.extend([
                fill_filter_fields(
                    FILTER_FIELD_CODE,
                    OPERATOR_IN,
                    get_code_list(f"@SOBJECT(sthpw/task['process', 'in', '{process_values}']['status', 'in', '{status_values}'].complex/scenes)", PROJECT_NAME)),
                fill_filter_fields(field_list[2], OPERATOR_IN, duration_values)
            ])
        
        case 2:
            duration_values = list(filter(None, values[1].split('&')))

            if field_list[0] == "PROC" and field_list[1] == "STAT":
                process_values = "|".join(values[0].split('&'))
                status_values = "|".join(values[1].split('&'))
                
                new_filter_fields.extend([fill_filter_fields(
                    FILTER_FIELD_CODE,
                    OPERATOR_IN,
                    get_code_list(f"@SOBJECT(sthpw/task['process', 'in', '{process_values}']['status', 'in', '{status_values}'].complex/scenes)", PROJECT_NAME)
                )])
            elif field_list[0] == "PROC" and field_list[1] != "STAT":
                process_values = "|".join(values[0].split('&'))
               
                new_filter_fields.extend([
                    fill_filter_fields(
                        FILTER_FIELD_CODE,
                        OPERATOR_IN,
                        get_code_list(f"@SOBJECT(sthpw/task['process', 'in', '{process_values}'].complex/scenes)", PROJECT_NAME)),
                    fill_filter_fields(field_list[1], OPERATOR_IN, duration_values)
                ])
            elif field_list[0] == "STAT" and field_list[1] != "PROC":
                status_values = "|".join(values[0].split('&'))
                
                new_filter_fields.extend([
                    fill_filter_fields(
                        FILTER_FIELD_CODE,
                        OPERATOR_IN,
                        get_code_list(f"@SOBJECT(sthpw/task['status', 'in', '{status_values}'].complex/scenes)", PROJECT_NAME)),
                    fill_filter_fields(field_list[1], OPERATOR_IN, duration_values)
                ])
        
        case 1:
            if field_list[0] == "PROC":
                process_values = "|".join(values[0].split('&'))
                
                new_filter_fields.extend([
                    fill_filter_fields(
                        FILTER_FIELD_CODE,
                        OPERATOR_IN,
                        get_code_list(f"@SOBJECT(sthpw/task['process', 'in', '{process_values}'].complex/scenes)", PROJECT_NAME))
                ])
            else:
                status_values = "|".join(values[0].split('&'))
                
                new_filter_fields.extend([
                    fill_filter_fields(
                        FILTER_FIELD_CODE,
                        OPERATOR_IN,
                        get_code_list(f"@SOBJECT(sthpw/task['status', 'in', '{status_values}'].complex/scenes)", PROJECT_NAME))
                ])

    return new_filter_fields


def add_assets_in_scenes(scene_code):
    Batch(PROJECT_NAME)
    assets = Search.eval(f"@SOBJECT(dolly3d/assets_in_scenes['scenes_code', '=', '{scene_code}'])")

    if not assets: return '0/0'

    assets_code = list(set(asset.get('assets_code') for asset in assets))
    complete_assets = Search.eval(f"@SOBJECT(sthpw/task['search_code', 'in', '{'|'.join(assets_code)}']['status', 'in', 'Опубликован|publish'])")

    return f'{len(complete_assets)}/{len(assets_code)}'


def get_assets_per_scenes(episodes_dict, episodes_codes):
    """
    This function takes two parameters: episodes_dict and episodes_codes.
    It returns a dictionary with the number of assets per episode.

    Parameters:
    episodes_dict (dict): A dictionary containing the episodes.
    episodes_codes (list): A list of episode codes.

    Returns:
    dict: A dictionary with the number of assets per episode.
    """

    # Connect to the TACTIC server
    server = TACTIC.get()
    server.set_project(PROJECT_NAME)

    # Get all assets in the given episodes
    assets = server.eval(f"@SOBJECT(dolly3d/assets_in_scenes['scenes_code', 'in', '{'|'.join(episodes_codes)}'])")

    # If there are no assets, return the episodes dict with 0/0 assets
    if assets == []:
        for episode in episodes_dict:
            episode['assets'] = '0/0'
        return episodes_dict

    # Get a list of all assets in the given episodes
    assets_per_episodes_all = {}
    for episode in episodes_codes:
        for asset in assets:
            if episode == asset['scenes_code']:
                assets_per_episodes_all.setdefault(episode, set()).add(asset.get('assets_code'))
            else:
                assets_per_episodes_all.setdefault(episode, set())

    # Get a list of all published assets in the given episodes
    code = "|".join(asset.get('assets_code') for asset in assets)
    complete_assets = server.eval(f"@SOBJECT(sthpw/task['search_code', 'in', '{code}']['status', 'in', 'Опубликован|publish'])")
    assets_per_episode = {}
    for episode in episodes_codes:
        for complete_asset in complete_assets:
            for asset in assets:
                if asset['assets_code'] == complete_asset['search_code']:
                    if episode == asset['scenes_code']: assets_per_episode.setdefault(episode, set()).add(complete_asset.get('search_code'))
                    else: assets_per_episode.setdefault(episode, set())

    # Add the number of assets to the episodes dict
    for episode in episodes_dict:
        code = episode.get('code')
        episode['assets'] = f'{len(assets_per_episode[code])}/{len(assets_per_episodes_all[code])}'

    return episodes_dict


import re
URL_PATTERN = re.compile(r"(?P<url>https?://[\w\d:#@%/;!$()~_?\+-=\\\.&]*[\w\d/#@%=_])", re.MULTILINE | re.UNICODE)

def search_links(description, pattern=URL_PATTERN):
    """
    This function searches for links in a given string.
    
    Parameters:
    description (str): The string to search for links in.
    
    Returns:
    list: A list of links found in the string.
    """
    if not isinstance(description, str):
        raise TypeError("Input parameter must be a string")
    
    if not description:
        return []
    
    if re.search(pattern.pattern, description):
        return pattern.sub(r'|\1', description).split('|')
    else:
        return description

def parse_descriptions(data):
    if isinstance(data, list):
        for rec in data:
            rec['description'] = search_links(rec.get('description')) if rec.get('description') else None
    else:
        data['description'] = search_links(data['description']) if data.get('description') else None

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
    """
    This class is used to get a list of resources from the database.
    """
    def __init__(self,
                 resource,
                 filters,
                 limit=0,
                 offset=0,
                 order_bys={'order_bys': 'id', 'ord_direction': 'asc'}
                 ):
        """
        Initializes the GetListQuery class.

        Parameters:
            resource (str): The resource to be retrieved.
            filters (dict): The filters to be applied to the query.
            limit (int): The maximum number of results to return.
            offset (int): The offset of the results to return.
            order_bys (dict): The order by clause to be applied to the query.
        """
        super(GetListQuery, self).__init__()
        self.limit = limit
        self.offset = offset
        self.ord_field = order_bys['order_bys']
        self.ord_direction = order_bys['ord_direction']
        self.filters = filters
        self.resource = resource

    @staticmethod
    def parse_filter_data(data):

        """
        Parse and filter data from a given list.

        Args:
            data (list): A list of dictionaries containing the data to be filtered.

        Returns:
            list: A list of dictionaries containing the filtered data.

        """

        filter_list = []
        if len(data) > 0:
            if data[0].get('field') == 'assets_category_code|AND':
                data.reverse()

            temp_data = []
            for index, record in enumerate(data):
                if record.get('field').find('PROC') >= 0 or record.get('field').find('STAT') >= 0:
                    temp_data = parse_filter(record)
                    data.pop(index)
            data.extend(temp_data)

            if data:
                for record in data:
                    operator = record.get('operator')
                    values = record.get('value')

                    if values == [None]: return None

                    fields = record.get('field').split('|')
                    if operator in ['contains', 'startswith', 'startsWith', 'starts with', 'starts With', 'endswith', 'endsWith', 'ends with', 'ends With']:
                        operator = 'EQI'
                    elif operator == 'null': operator, values = '=', None
                    elif operator == 'nnull': operator, values = '!=', ''
                    elif operator == ['isAnyOf', 'in']: operator = 'in'
                    elif operator == 'eq': operator = '='

                    for field in fields:
                        if field == '' or field is None:
                            pass
                        else:
                            if field == 'AND':
                                filter_list[-1]['method'] = 'and'
                            else:
                                filter_list.append({'field': field, 'value': values, 'op': operator, 'method': 'or'})
                return filter_list
            else:
                return None

    def execute(self):
        """
        Executes the GetListQuery command.

        Returns:
            dict: A dictionary containing the data and total number of results.
        """
        main_time = time_it()
        resource = match_resource(self.resource)

        if resource['search_type'] == 'pipes':
            if len(self.filters) > 0:
                code = self.filters[0].get('value')
            else:
                return {'data': 0,'total': 0}

            data = get_pipeline_process_info(code=code, project=PROJECT_NAME)
            return {'data': data,'total': len(data)}

        if resource['search_type'] == 'durations':
            return get_duration()


        Batch(resource['project'])
        s_object = Search(resource['search_type'])

        s_filter = self.parse_filter_data(self.filters)

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
        search_results = s_object.get_sobjects()
        
        search_keys = {resource['search_type'] + ('?project=' + resource['project'] if resource.get('project') else ''):
               [res.get_sobject_dict().get('__search_key__').split('=')[-1] for res in search_results] }
        episodes_codes = [result.get_code() for result in search_results if resource['search_type'] == 'complex/scenes']
        output = [result.get_sobject_dict() for result in search_results]

        if search_keys:
            output = get_images_urls(output, search_keys)

        if resource['search_type'] == 'complex/scenes':
            output = get_assets_per_scenes(output, episodes_codes)

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
