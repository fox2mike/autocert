#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re

from flask import make_response, jsonify

from pprint import pprint, pformat
from attrdict import AttrDict
from fnmatch import fnmatch
from ruamel import yaml
from json import dumps
from flask import jsonify

from tardata import Tardata
from authority.factory import create_authority
from destination.factory import create_destination
from utils.asyncrequests import AsyncRequests
from utils import timestamp

from utils import tar
from utils.format import fmt, pfmt
from utils.dictionary import merge, head, head_body

from app import app
from config import CFG

class EndpointBase(object):
    _sorting_funcs = dict(
        default=lambda cert: cert.common_name,
        timestamp=lambda cert: cert.timestamp,
        expiry=lambda cert: cert.expiry)

    def __init__(self, cfg, args):
        self.ar = AsyncRequests()
        self.cfg = AttrDict(cfg)
        self.args = AttrDict(args)
        self.verbosity = self.args.verbosity
        authorities = self.cfg.authorities
        self.authorities = AttrDict({
            a: create_authority(a, self.ar, authorities[a], self.verbosity) for a in authorities
        })
        destinations = self.cfg.destinations
        self.destinations = AttrDict({
            d: create_destination(d, self.ar, destinations[d], self.verbosity) for d in destinations
        })
        self.tardata = Tardata(self.cfg.tar.dirpath, self.verbosity)

    @property
    def authority(self):
        return self.authorities[self.args.authority]

    @property
    def timestamp(self):
        return self.tardata.timestamp

    @property
    def calls(self):
        return self.ar.calls

    @property
    def sorting_func(self):
        return EndpointBase._sorting_funcs[self.args.sorting]

    def execute(self, **kwargs):
        raise NotImplementedError

    def transform(self, certs):
        json = dict(
            certs=[cert.transform(self.verbosity) for cert in sorted(certs, key=self.sorting_func)],
        )
        if self.args.call_detail:
            calls = [self.transform_call(call) for call in self.ar.calls]
            json['calls'] = calls
        return json

    def transform_call(self, call):
        name = '{0} {1} {2}'.format(call.recv.status, call.send.method, call.send.url)
        if self.args.call_detail == 'summary':
            return name
        return {name: dict(send=call.send, recv=call.recv)}

    def sanitize(self, cert_name_pn, ext='.tar.gz'):
        if cert_name_pn.endswith(ext):
            cert_name_pn = cert_name_pn[0:-len(ext)]
        cert_name_pn = os.path.basename(cert_name_pn)
        regex = re.compile('([A-Za-z0-9\.\-_]+)(@([A-Fa-f0-9]{8}))?')
        match = regex.search(cert_name_pn)
        if match:
            common_name, _, modhash = match.groups()
            if modhash:
                return cert_name_pn
            if common_name.endswith('*'):
                return common_name
            return common_name + '*'
        return cert_name_pn

