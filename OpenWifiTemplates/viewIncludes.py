from pyramid.response import Response
from pyramid.view import view_config, forbidden_view_config
from pyramid.httpexceptions import HTTPFound
from pyramid_rpc.jsonrpc import jsonrpc_method
from pyramid import httpexceptions as exc
import transaction
import random
from datetime import datetime
import string
import pprint
from openwifi.jobserver_config import redishost, redisport, redisdb
import redis
from wsgiproxy import Proxy

import shutil
import os

import json
from pyuci import Uci
import openwifi.jobserver.tasks as jobtask

from sqlalchemy.exc import DBAPIError
from sqlalchemy.sql.expression import func as sql_func

from openwifi.models import (
    AccessPoint,
    DBSession,
    OpenWrt,
    ConfigArchive,
    Templates,
    SshKey,
    OpenWifiSettings
    )

from .forms import (
        AccessPointAddForm,
        OpenWrtEditForm,
        LoginForm,
        SshKeyForm,
        SettingsForm
        )

from openwifi.utils import generate_device_uuid

from pyramid.security import (
   Allow,
   Authenticated,
   remember,
   forget)
