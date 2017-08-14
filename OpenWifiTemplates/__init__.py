globalWebViews = [['templates','Templates']]

def addPluginRoutes(config):
    addTemplatesRoutes(config)

def addTemplatesRoutes(config):
    config.add_route('templates', '/templates')
    config.add_route('templates_add', '/templates_add')
    config.add_route('templates_assign', '/templates_assign/{id}')
    config.add_route('templates_edit', '/templates_edit/{id}')
    config.add_route('templates_delete', '/templates_delete/{id}')
    config.add_route('templates_action', '/templates/{id}/{action}')

def update_template(openwrtConfJSON, templateJSON):
    openwrt_config = Uci()
    openwrt_config.load_tree(openwrtConfJSON)
    metaconf = json.loads(templateJSON)['metaconf']
    for package in metaconf['change']['add']: # packages to be added
        if  package not in openwrt_config.packages.keys():
            openwrt_config.add_package(package)
    for package in metaconf['change']['del']: # packages to be deleted
        if package in openwrt_config.packages.keys():
            openwrt_config.packages.pop(package)
    packages = metaconf['packages']
    for package_match in packages:
        if not package_match['type']=='package':
            raise MetaconfWrongFormat('first level should be type: \
                     package, but found: '+ cur_package_match['type']) 
        package = package_match['matchvalue']
        # scan for packages to be added and add
        for config in package_match['change']['add']:
            nameMismatch = True
            typeMismatch = True
            # match names
            if config[0] in openwrt_config.packages[package].keys():
                nameMismatch = False
            # match types
            for confname, conf in openwrt_config.packages[package].items():
                if conf.uci_type == config[1]:
                    typeMismatch = False
                    break
            if (config[2] == 'always') or\
               (config[2] == 'typeMismatch' and typeMismatch) or\
               (config[2] == 'nameMismatch' and nameMismatch) or\
               (config[2] == 'bothMismatch' and typeMismatch and nameMismatch):
                openwrt_config.packages[package][config[0]] = Config(config[1],config[0],config[0]=='') #Config(ucitype, name, anon)
        # scan for packages to be removed and delete
        for config in package_match['change']['del']:
            confmatch = config[2]
            # match names
            if config[0] in openwrt_config.packages[package].keys():
                if confmatch == 'always'  or confmatch == 'nameMatch':
                    openwrt_config.packages[package].pop(config[0])
            # match types
            for confname, conf in openwrt_config.packages[package].items():
                if conf.uci_type == config[1]:
                    if confmatch == 'always' or confmatch == 'typeMatch':
                        openwrt_config.packages[package].pop(confname)
                    if confmatch == 'bothMatch' and confname == conf[0]:
                        openwrt_config.packages[package].pop(confname)
        # go into config matches
        for conf_match in  package_match['config']:
            matched_configs = []
            configs_to_be_matched = list(openwrt_config.packages[package].values())
            while conf_match!='' and configs_to_be_matched:
                for config in configs_to_be_matched:
                    if conf_match['matchtype']=='name':
                        if config.name==conf_match['matchvalue']:
                            matched_configs.append(config)
                    if conf_match['matchtype']=='type':
                        if config.uci_type==conf_match['ucitype']:
                            matched_configs.append(config)
                for mconfig in matched_configs:
                    for option in conf_match['change']['add']:
                        mconfig.keys[option[0]] = option[1]
                    for option in conf_match['change']['del']:
                        try:
                            mconfig.keys.pop(option)
                        except KeyError:
                            pass
                    # new options that might not be in older templates
                    try:
                        for option in conf_match['change']['appendToList']:
                            if type(mconfig.keys[option[0]]) is list and option[1] not in mconfig.keys[option[0]]:
                                mconfig.keys[option[0]].append(option[1])
                        for option in conf_match['change']['removeFromList']:
                            if type(mconfig.keys[option[0]]) is list and option[1]  in mconfig.keys[option[0]]:
                                indexInList = mconfig.keys[option[0]].index(option[1])
                                mconfig.keys[option[0]].pop(indexInList)
                    except KeyError:
                        pass
                configs_to_be_matched=matched_configs
                conf_match=conf_match['next']
    return openwrt_config

def addJobserverTasks(app):
    @app.task
    def update_template_config(id):
            DBSession = get_sql_session()
            template = DBSession.query(Templates).get(id)
            for openwrt in template.openwrt:
                newconf = update_template(openwrt.configuration, template.metaconf)
                openwrt.configuration = newconf.export_json()
            DBSession.commit()
            for openwrt in template.openwrt:
                updateconf = signature('openwifi.jobserver.tasks.update_config',
                                     args=(openwrt.uuid,))
                updateconf.delay()
            DBSession.close()
