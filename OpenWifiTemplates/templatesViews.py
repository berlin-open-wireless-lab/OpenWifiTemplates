from OpenWifiWeb.viewIncludes import *
from openwifi.utils import id_generator

@view_config(route_name='templates', renderer='templates/templates.jinja2', layout='base', permission='view')
def templates(request):
    templates = DBSession.query(Templates)
    openwrts = {}
    for template in templates:
        openwrts[template.id] = []
        for openwrt in template.openwrt:
            openwrts[template.id].append({ 'uuid' : openwrt.uuid, \
                                           'name' : openwrt.name})
    return {'items': templates,
            'openwrts' : openwrts,
            'table_fields': ['name', 'id', 'metaconf', 'openwrt'],
            'actions' : ['update']}

@view_config(route_name='templates_delete', renderer='templates/templates.jinja2', layout='base', permission='view')
def templates_delete(request):
    template = DBSession.query(Templates).get(request.matchdict['id'])
    if not template:
        return exc.HTTPNotFound()
    DBSession.delete(template)
    return HTTPFound(location=request.route_url('templates'))

@view_config(route_name='templates_edit', renderer='templates/templates_add.jinja2', layout='base', permission='view')
def templates_edit(request):
    template = DBSession.query(Templates).get(request.matchdict['id'])
    if not template:
        return exc.HTTPNotFound()
    if request.POST:
        metaconf_json, templateName = generateMetaconfJson(request.POST)
        template.metaconf = metaconf_json
        template.name = templateName
        return HTTPFound(location=request.route_url('templates'))
    return { 'metaconf' : template.metaconf,
             'templateName' : template.name}
    
@view_config(route_name='templates_add', renderer='templates/templates_add.jinja2', layout='base', permission='view')
def templates_add(request):
    if request.POST:
        metaconf_json, templateName = generateMetaconfJson(request.POST)
        newTemplate = Templates(templateName,metaconf_json,id_generator())
        DBSession.add(newTemplate)
        return HTTPFound(location=request.route_url('templates'))
    return {'metaconf' : '{}',
            'templateName':''}

@view_config(route_name='templates_assign', renderer='templates/archive_apply_config.jinja2', layout='base', permission='view')
def templates_assign(request):
    template = DBSession.query(Templates).get(request.matchdict['id'])
    if not template:
        return exc.HTTPNotFound()

    from openwifi.authentication import get_nodes
    openwrt = get_nodes(request)
    devices = {}
    if request.POST:
        owned_nodes = get_nodes(request)
        owned_nodes_dict = {}
        for node in owned_nodes:
            owned_nodes_dict[str(node.uuid)] = node

        for ow in openwrt:
            try:
                ow.templates.remove(template)
            except ValueError: # if the template is not assoc - do nothing
                pass
        for name,value in request.POST.dict_of_lists().items():
            if name!='submitted':
                if name not in owned_nodes_dict:
                    continue

                device = owned_nodes_dict[name]
                if  value: # if item is not the submit button and it's checkd
                    device.templates.append(template)
        return HTTPFound(location = request.route_url('templates'))
    for device in openwrt:
        name = str(device.name)
        while name in devices.keys():
            name += '_'
        devices[name] = str(device.uuid)
    checked = []
    for device in template.openwrt:
        checked.append(str(device.uuid))
    return { 'devices' : devices,
             'checked' : checked}

@view_config(route_name='templates_action', renderer='templates/templates.jinja2', layout='base', permission='view')
def templates_action(request):
    action = request.matchdict['action']
    template = DBSession.query(Templates).get(request.matchdict['id'])
    if not template:
        return exc.HTTPNotFound()

    if action == 'update':
        jobtask.update_template_config.delay(template.id)
        return HTTPFound(location=request.route_url('templates'))

    return exc.HTTPNotFound()

def generateMetaconfJson(POST):
        # init metaconf
        metaconf = {}
        metaconf['metaconf'] = {}
        metaconf['metaconf']['change']= {}
        metaconf['metaconf']['change']['add']= []
        metaconf['metaconf']['change']['del']= []
        metaconf['metaconf']['packages']= []

        # dictonary to store data from form
        formdata = {}
        # first read all values into formdata
        for key, val in POST.dict_of_lists().items():
            keysplit = key.split('.')
            curlevel=formdata
            i=1
            for splittedkey in keysplit:
                if(i<len(keysplit)):
                    try:
                        curlevel=curlevel[splittedkey]
                    except KeyError:
                        curlevel[splittedkey]={}
                        curlevel=curlevel[splittedkey]
                else:
                    curlevel[splittedkey]=val[0]
                i+=1

        templateName = formdata.pop('templateName')
        pp = pprint.PrettyPrinter(indent=4)
        # go thru configs
        for key, val in formdata.items():
            if key[0:7] == "package":
                # add new package
                if key[7] == "A":
                    # init new package
                    curpack = {}
                    curpack['type'] = "package"
                    curpack['matchvalue'] = val['Name']
                    curpack['config'] = []
                    curpack['change'] = {}
                    curpack['change']['add'] = []
                    curpack['change']['del'] = []

                    try:
                        if val['Add']=="on":
                            metaconf['metaconf']['change']['add'].append(val['Name'])
                    except KeyError: #don't add if no key
                        pass
                    for pkey in val.keys():
                        if pkey[0:6] == 'config':
                            if pkey[6] == "A":
                                mconfig = {}
                                config = mconfig
                                curconfig = val[pkey]
                                while True:
                                    try:
                                        if curconfig['Add']=='on':
                                            curpack['change']['add'].append(  \
                                                [curconfig['Name'], \
                                                 curconfig['Type'], \
                                                 curconfig['CreateType']])
                                    except KeyError: # don't add if we have not received to add
                                        pass
                                    config['matchvalue']=curconfig['Name']
                                    config['matchtype']=curconfig['matchtype']
                                    config['ucitype']=curconfig['Type']
                                    config['matchcount']=curconfig['Count']
                                    config['type']='config'
                                    config['change']={}
                                    config['change']['add']=[]
                                    config['change']['del']=[]
                                    config['change']['appendToList']=[]
                                    config['change']['removeFromList']=[]
                                    optsToAdd = [value for key, value in curconfig.items() if key.startswith('optA')]
                                    for opt in optsToAdd:
                                        if opt['Type'] == 'normal':
                                            config['change']['add'].append(\
                                                    [opt['Name'], \
                                                     opt['Value']])
                                        elif opt['Type'] == 'appendToList':
                                            config['change']['appendToList'].append(\
                                                    [opt['Name'], \
                                                     opt['Value']])
                                        elif opt['Type'] == 'removeFromList':
                                            config['change']['removeFromList'].append(\
                                                    [opt['Name'], \
                                                     opt['Value']])
                                        elif opt['Type'] == 'isList':
                                            config['change']['add'].append(\
                                                    [opt['Name'], \
                                                     json.loads(opt['Value'])])
                                    optsToDel = [value for key, value in curconfig.items() if key.startswith('optD')]
                                    for opt in optsToDel:
                                        config['change']['del'].append(\
                                                opt['Name'])
                                    nextconfigs = [value for key, value in curconfig.items() if key.startswith('configA')]
                                    if nextconfigs:
                                        curconfig = nextconfigs[0]
                                        config['next'] = {}
                                        config = config['next']
                                    else:
                                        config['next'] = ''
                                        break
                                curpack['config'].append(mconfig)
                            if pkey[6] == "D":
                                curpack['change']['del'].append(  \
                                        [val[pkey]['Name'], \
                                         val[pkey]['Type'], \
                                         val[pkey]['DelType']])
                    metaconf['metaconf']['packages'].append(curpack)
                # delete package
                if key[7] == "D":
                    metaconf['metaconf']['change']['del'].append(val['Name'])
            else:
                print("ERROR: first level should be a package")
        pp.pprint(POST)
        pp.pprint(formdata)
        pp.pprint(metaconf)
        pp.pprint(templateName)
        metaconf_json = json.dumps(metaconf)
        return metaconf_json, templateName
