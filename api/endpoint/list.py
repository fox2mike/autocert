#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re

from attrdict import AttrDict
from fnmatch import fnmatch
from ruamel import yaml

from utils.dictionary import merge, head, head_body
from utils.format import fmt, pfmt
from app import app
from config import CFG
from endpoint.base import EndpointBase
from authority.factory import create_authority
from destination.factory import create_destination
from utils.output import yaml_format

class ListEndpoint(EndpointBase):
    def __init__(self, cfg, args):
        super(ListEndpoint, self).__init__(cfg, args)

    def execute(self, **kwargs):
        status = 200
        cert_name_pns = [self.sanitize(cert_name_pn) for cert_name_pn in self.args.cert_name_pns]
        certs = self.tardata.load_certs(
            *cert_name_pns,
            within=self.args.within,
            expired=self.args.expired)
        certs2 = []
        if self.verbosity > 1:
            #FIXME: this should be driven by the yml in the cert tarball
            certs1 = self.authorities.digicert.display_certificates(certs)
            for name, dests in self.args.destinations.items():
                pfmt('name={name} dests={dests}')
                certs2.extend(self.destinations[name].fetch_certificates(certs1, *dests))
        else:
            certs2 = certs
        json = self.transform(certs2)
        return json, status

