# Copyright 2017-2018 CERN for the benefit of the ATLAS collaboration.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Authors:
# - Vincent Garonne <vgaronne@gmail.com>, 2017-2018
# - Martin Barisits <martin.barisits@cern.ch>, 2017
# - Joaquin Bogado <jbogado@linti.unlp.edu.ar>, 2018
# - Mario Lassnig <mario.lassnig@cern.ch>, 2018

from nose.tools import assert_equal, assert_in

from rucio.client.didclient import DIDClient
from rucio.client.replicaclient import ReplicaClient
from rucio.common.utils import generate_uuid
from rucio.core.replica import add_replicas, delete_replicas
from rucio.core.rse import add_rse, del_rse, add_protocol
from rucio.tests.common import rse_name_generator


class TestArchive(object):

    def __init__(self):
        self.dc = DIDClient()
        self.rc = ReplicaClient()

    def test_add_and_list_archive(self):
        """  ARCHIVE (CLIENT): Add files to archive and list the content """
        scope, rse = 'mock', 'MOCK'
        archive_files = ['file_' + generate_uuid() + '.zip' for _ in range(2)]
        files = []
        for i in range(10):
            files.append({'scope': scope, 'name': 'lfn.%s' % str(generate_uuid()),
                          'bytes': 724963570,
                          'adler32': '0cc737eb',
                          'type': 'FILE',
                          'meta': {'guid': str(generate_uuid())}})
        for archive_file in archive_files:

            self.rc.add_replicas(rse=rse, files=[{'scope': scope,
                                                  'name': archive_file,
                                                  'bytes': 1,
                                                  'adler32': '0cc737eb'}])

            self.dc.add_files_to_archive(scope=scope, name=archive_file, files=files)

            content = [f for f in self.dc.list_archive_content(scope=scope, name=archive_file)]

            assert_equal(len(content), 10)

    def test_list_archive_contents_transparently(self):
        """ ARCHIVE (CORE): Transparent archive listing """

        scope = 'mock'
        rse = 'APERTURE_%s' % rse_name_generator()
        add_rse(rse)

        files = [{'scope': scope, 'name': 'element%i.%s' % (i, str(generate_uuid())), 'type': 'FILE',
                  'bytes': 1234, 'adler32': 'deadbeef'} for i in xrange(2)]
        add_replicas(rse=rse, files=files, account='root')
        add_protocol(rse, {'scheme': 'root',
                           'hostname': 'root.aperture.com',
                           'port': 1409,
                           'prefix': '//test/chamber/',
                           'impl': 'rucio.rse.protocols.xrootd.Default',
                           'domains': {
                               'lan': {'read': 1, 'write': 1, 'delete': 1},
                               'wan': {'read': 1, 'write': 1, 'delete': 1}}})

        res = [r['pfns'] for r in self.rc.list_replicas(dids=[{'scope': scope, 'name': f['name']} for f in files])]
        assert_equal(len(res), 2)

        archive = {'scope': scope, 'name': 'weighted.companion.cube.zip', 'type': 'FILE',
                   'bytes': 2596, 'adler32': 'beefdead'}
        add_replicas(rse=rse, files=[archive], account='root')
        self.dc.add_files_to_archive(scope=scope, name=archive['name'], files=files)

        res = [r['pfns'] for r in self.rc.list_replicas(dids=[{'scope': scope, 'name': f['name']} for f in files])]
        delete_replicas(rse=rse, files=files)
        delete_replicas(rse=rse, files=[archive])
        del_rse(rse)

        zipped_pfns = list(zip(*res))[0]
        assert_in('root://root.aperture.com:1409//test/chamber/mock/81/ce/weighted.companion.cube.zip?xrdcl.unzip=element', zipped_pfns[0])
        assert_in('root://root.aperture.com:1409//test/chamber/mock/81/ce/weighted.companion.cube.zip?xrdcl.unzip=element', zipped_pfns[1])
        assert_equal(len(zipped_pfns), 2)
