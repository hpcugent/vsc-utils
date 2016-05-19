#
# Copyright 2012-2016 Ghent University
#
# This file is part of vsc-utils,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/hpcugent/vsc-utils
#
# vsc-utils is free software: you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License as
# published by the Free Software Foundation, either version 2 of
# the License, or (at your option) any later version.
#
# vsc-utils is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with vsc-utils. If not, see <http://www.gnu.org/licenses/>.
#
"""
Utilities to allow interacting with a REST API as an application that
was registered with the OAuth system of the web application.
"""
import jsonpickle
import urllib
import urllib2


def request_access_token(opener, path, client_id, client_secret):
    """
    Make a call to the oauth api to obtain an access token.
    """
    payload = urllib.urlencode({"grant_type": "client_credentials",
                                "client_id": client_id,
                                "client_secret": client_secret})
    request = urllib2.Request(path, payload)
    request.add_header('Content-Type', 'application/json')
    request.get_method = lambda: 'POST'
    uri = opener.open(request)
    response = uri.read()
    return jsonpickle.decode(response)



def make_api_request(opener, path, method='GET', payload="", access_token=""):
    """
    Make a call to the REST API, given an access token.
    """
    request = urllib2.Request(path, payload)
    request.add_header('Content-Type', 'application/json')
    request.add_header('Authorization', "Bearer %s" % (access_token,))
    request.get_method = lambda: method
    uri = opener.open(request)
    response = uri.read()
    return jsonpickle.decode(response)





