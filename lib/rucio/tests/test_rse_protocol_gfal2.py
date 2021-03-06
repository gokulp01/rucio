# Copyright European Organization for Nuclear Research (CERN)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Authors:
# - Wen Guan, <wguan@cern.ch>, 2014

import json
import os
import shutil
import tempfile

from uuid import uuid4 as uuid

from nose.tools import raises

from rucio.common import exception
from rucio.rse import rsemanager as mgr
from rsemgr_api_test import MgrTestCases
from rucio.common.utils import execute


class TestRseGFAL2():
    tmpdir = None
    user = None

    @classmethod
    def setupClass(cls):
        """GFAL2 (RSE/PROTOCOLS): Creating necessary directories and files """
        # Creating local files
        cls.tmpdir = tempfile.mkdtemp()
        cls.user = uuid()

        with open("%s/data.raw" % cls.tmpdir, "wb") as out:
            out.seek((1024 * 1024) - 1)  # 1 MB
            out.write('\0')
        for f in MgrTestCases.files_local:
            shutil.copy('%s/data.raw' % cls.tmpdir, '%s/%s' % (cls.tmpdir, f))

        with open('etc/rse_repository.json') as f:
            data = json.load(f)
        prefix = data['FZK-LCG2_SCRATCHDISK']['protocols']['supported']['srm']['prefix']
        hostname = data['FZK-LCG2_SCRATCHDISK']['protocols']['supported']['srm']['hostname']
        if hostname.count("://"):
            hostname = hostname.split("://")[1]
        if 'port' in data['FZK-LCG2_SCRATCHDISK']['protocols']['supported']['srm'].keys():
            port = int(data['FZK-LCG2_SCRATCHDISK']['protocols']['supported']['srm']['port'])
        else:
            port = 0
        if 'extended_attributes' in data['FZK-LCG2_SCRATCHDISK']['protocols']['supported']['srm'].keys() and 'web_service_path' in data['FZK-LCG2_SCRATCHDISK']['protocols']['supported']['srm']['extended_attributes'].keys():
            web_service_path = data['FZK-LCG2_SCRATCHDISK']['protocols']['supported']['srm']['extended_attributes']['web_service_path']
        else:
            web_service_path = ''

        os.system('dd if=/dev/urandom of=%s/data.raw bs=1024 count=1024' % cls.tmpdir)
        if port > 0:
            cls.static_file = 'srm://%s:%s%s%s/data.raw' % (hostname, port, web_service_path, prefix)
        else:
            cls.static_file = 'srm://%s%s%s/data.raw' % (hostname, web_service_path, prefix)
        cmd = 'srmcp -2 --debug=false -retry_num=0 file:///%s/data.raw %s' % (cls.tmpdir, cls.static_file)
        execute(cmd)

        rse_settings = mgr.get_rse_info('FZK-LCG2_SCRATCHDISK')
        for protocol in rse_settings['protocols']:
            if protocol['scheme'] != "srm":
                rse_settings['protocols'].remove(protocol)
        if len(rse_settings['protocols']) > 0:
            rse_settings['protocols'][0]['impl'] = 'rucio.rse.protocols.gfal.Default'

        for f in MgrTestCases.files_remote:
            tmp = mgr.lfns2pfns(rse_settings, {'name': f, 'scope': 'user.%s' % cls.user}, scheme='srm').values()[0]
            cmd = 'srmcp -2 --debug=false -retry_num=0  file:///%s/data.raw %s' % (cls.tmpdir, tmp)
            execute(cmd)

    @classmethod
    def teardownClass(cls):
        """GFAL2 (RSE/PROTOCOLS): Removing created directorie s and files"""
        with open('etc/rse_repository.json') as f:
            data = json.load(f)
        prefix = data['FZK-LCG2_SCRATCHDISK']['protocols']['supported']['srm']['prefix']
        hostname = data['FZK-LCG2_SCRATCHDISK']['protocols']['supported']['srm']['hostname']
        if hostname.count("://"):
            hostname = hostname.split("://")[1]
        if 'port' in data['FZK-LCG2_SCRATCHDISK']['protocols']['supported']['srm'].keys():
            port = int(data['FZK-LCG2_SCRATCHDISK']['protocols']['supported']['srm']['port'])
        else:
            port = 0
        if 'extended_attributes' in data['FZK-LCG2_SCRATCHDISK']['protocols']['supported']['srm'].keys() and 'web_service_path' in data['FZK-LCG2_SCRATCHDISK']['protocols']['supported']['srm']['extended_attributes'].keys():
            web_service_path = data['FZK-LCG2_SCRATCHDISK']['protocols']['supported']['srm']['extended_attributes']['web_service_path']
        else:
            web_service_path = ''

        shutil.rmtree(cls.tmpdir)

        clean_raw = '%s/data.raw' % prefix
        if int(port) > 0:
            srm_path = ''.join(["srm://", hostname, ":", port, web_service_path])
        else:
            srm_path = ''.join(["srm://", hostname, web_service_path])

        list_files_cmd_user = 'srmls -2 --debug=false -retry_num=0 -recursion_depth=3 %s%s/user/%s' % (srm_path, prefix, cls.user)
        clean_files = str(execute(list_files_cmd_user)[1]).split('\n')
        list_files_cmd_user = 'srmls -2 --debug=false -retry_num=0 -recursion_depth=3 %s%s/group/%s' % (srm_path, prefix, cls.user)
        clean_files += str(execute(list_files_cmd_user)[1]).split('\n')
        clean_files.append("1024  " + clean_raw)
        for files in clean_files:
            if len(files.strip()) > 0:
                file = files.split()[1]
                if not file.endswith("/"):
                    clean_cmd = 'srmrm -2 --debug=false -retry_num=0 %s/%s' % (srm_path, file)
                    execute(clean_cmd)

        clean_directory = ['user', 'group']
        for directory in clean_directory:
            clean_cmd = 'srmrmdir -2 --debug=false -retry_num=0 -recursive %s%s/%s/%s' % (srm_path, prefix, directory, cls.user)
            execute(clean_cmd)

    def setup(self):
        """GFAL2 (RSE/PROTOCOLS): Creating Mgr-instance """
        self.tmpdir = TestRseGFAL2.tmpdir
        self.rse_id = 'FZK-LCG2_SCRATCHDISK'
        self.mtc = MgrTestCases(self.tmpdir, 'FZK-LCG2_SCRATCHDISK', TestRseGFAL2.user, TestRseGFAL2.static_file)
        # self.mtc = MgrTestCases(self.tmpdir, 'FZK-LCG2_SCRATCHDISK', TestRseGFAL2.user, "srm://atlassrm-fzk.gridka.de/pnfs/gridka.de/atlas/disk-only/atlasscratchdisk/user/wguan/rucio.test.2")
        self.mtc.setup_scheme('srm', 'gfal')

    # Mgr-Tests: GET
    def test_multi_get_mgr_ok(self):
        """GFAL2 (RSE/PROTOCOLS): Get multiple files from storage providing LFNs and PFNs (Success)"""
        self.mtc.test_multi_get_mgr_ok()

    def test_get_mgr_ok_single_lfn(self):
        """GFAL2 (RSE/PROTOCOLS): Get a single file from storage providing LFN (Success)"""
        self.mtc.test_get_mgr_ok_single_lfn()

    def test_get_mgr_ok_single_pfn(self):
        """GFAL2 (RSE/PROTOCOLS): Get a single file from storage providing PFN (Success)"""
        self.mtc.test_get_mgr_ok_single_pfn()

    @raises(exception.SourceNotFound)
    def test_get_mgr_SourceNotFound_multi(self):
        """GFAL2 (RSE/PROTOCOLS): Get multiple files from storage providing LFNs and PFNs (SourceNotFound)"""
        self.mtc.test_get_mgr_SourceNotFound_multi()

    @raises(exception.SourceNotFound)
    def test_get_mgr_SourceNotFound_single_lfn(self):
        """GFAL2 (RSE/PROTOCOLS): Get a single file from storage providing LFN (SourceNotFound)"""
        self.mtc.test_get_mgr_SourceNotFound_single_lfn()

    @raises(exception.SourceNotFound)
    def test_get_mgr_SourceNotFound_single_pfn(self):
        """GFAL2 (RSE/PROTOCOLS): Get a single file from storage providing PFN (SourceNotFound)"""
        self.mtc.test_get_mgr_SourceNotFound_single_pfn()

    # Mgr-Tests: PUT
    def test_put_mgr_ok_multi(self):
        """GFAL2 (RSE/PROTOCOLS): Put multiple files to storage providing LFNs and PFNs (Success)"""
        self.mtc.test_put_mgr_ok_multi()

    def test_put_mgr_ok_single(self):
        """GFAL2 (RSE/PROTOCOLS): Put a single file to storage (Success)"""
        self.mtc.test_put_mgr_ok_single()

    @raises(exception.SourceNotFound)
    def test_put_mgr_SourceNotFound_multi(self):
        """GFAL2 (RSE/PROTOCOLS): Put multiple files to storage (SourceNotFound)"""
        self.mtc.test_put_mgr_SourceNotFound_multi()

    @raises(exception.SourceNotFound)
    def test_put_mgr_SourceNotFound_single(self):
        """GFAL2 (RSE/PROTOCOLS): Put a single file to storage (SourceNotFound)"""
        self.mtc.test_put_mgr_SourceNotFound_single()

    @raises(exception.FileReplicaAlreadyExists)
    def test_put_mgr_FileReplicaAlreadyExists_multi(self):
        """GFAL2 (RSE/PROTOCOLS): Put multiple files to storage (FileReplicaAlreadyExists)"""
        self.mtc.test_put_mgr_FileReplicaAlreadyExists_multi()

    @raises(exception.FileReplicaAlreadyExists)
    def test_put_mgr_FileReplicaAlreadyExists_single(self):
        """GFAL2 (RSE/PROTOCOLS): Put a single file to storage (FileReplicaAlreadyExists)"""
        self.mtc.test_put_mgr_FileReplicaAlreadyExists_single()

    # MGR-Tests: DELETE
    def test_delete_mgr_ok_multi(self):
        """GFAL2 (RSE/PROTOCOLS): Delete multiple files from storage (Success)"""
        self.mtc.test_delete_mgr_ok_multi()

    def test_delete_mgr_ok_single(self):
        """GFAL2 (RSE/PROTOCOLS): Delete a single file from storage (Success)"""
        self.mtc.test_delete_mgr_ok_single()

    @raises(exception.SourceNotFound)
    def test_delete_mgr_SourceNotFound_multi(self):
        """GFAL2 (RSE/PROTOCOLS): Delete multiple files from storage (SourceNotFound)"""
        self.mtc.test_delete_mgr_SourceNotFound_multi()

    @raises(exception.SourceNotFound)
    def test_delete_mgr_SourceNotFound_single(self):
        """GFAL2 (RSE/PROTOCOLS): Delete a single file from storage (SourceNotFound)"""
        self.mtc.test_delete_mgr_SourceNotFound_single()

    # MGR-Tests: EXISTS
    def test_exists_mgr_ok_multi(self):
        """GFAL2 (RSE/PROTOCOLS): Check multiple files on storage (Success)"""
        self.mtc.test_exists_mgr_ok_multi()

    def test_exists_mgr_ok_single_lfn(self):
        """GFAL2 (RSE/PROTOCOLS): Check a single file on storage using LFN (Success)"""
        self.mtc.test_exists_mgr_ok_single_lfn()

    def test_exists_mgr_ok_single_pfn(self):
        """GFAL2 (RSE/PROTOCOLS): Check a single file on storage using PFN (Success)"""
        self.mtc.test_exists_mgr_ok_single_pfn()

    def test_exists_mgr_false_multi(self):
        """GFAL2 (RSE/PROTOCOLS): Check multiple files on storage (Fail)"""
        self.mtc.test_exists_mgr_false_multi()

    def test_exists_mgr_false_single(self):
        """GFAL2 (RSE/PROTOCOLS): Check a single file on storage using LFN (Fail)"""
        self.mtc.test_exists_mgr_false_single_lfn()

    def test_exists_mgr_false_single_pfn(self):
        """GFAL2 (RSE/PROTOCOLS): Check a single file on storage using PFN (Fail)"""
        self.mtc.test_exists_mgr_false_single_pfn()

    # MGR-Tests: RENAME
    def test_rename_mgr_ok_multi(self):
        """GFAL2 (RSE/PROTOCOLS): Rename multiple files on storage (Success)"""
        self.mtc.test_rename_mgr_ok_multi()

    def test_rename_mgr_ok_single_lfn(self):
        """GFAL2 (RSE/PROTOCOLS): Rename a single file on storage using LFN (Success)"""
        self.mtc.test_rename_mgr_ok_single_lfn()

    def test_rename_mgr_ok_single_pfn(self):
        """GFAL2 (RSE/PROTOCOLS): Rename a single file on storage using PFN (Success)"""
        self.mtc.test_rename_mgr_ok_single_pfn()

    @raises(exception.FileReplicaAlreadyExists)
    def test_rename_mgr_FileReplicaAlreadyExists_multi(self):
        """GFAL2 (RSE/PROTOCOLS): Rename multiple files on storage (FileReplicaAlreadyExists)"""
        self.mtc.test_rename_mgr_FileReplicaAlreadyExists_multi()

    @raises(exception.FileReplicaAlreadyExists)
    def test_rename_mgr_FileReplicaAlreadyExists_single_lfn(self):
        """GFAL2 (RSE/PROTOCOLS): Rename a single file on storage using LFN(FileReplicaAlreadyExists)"""
        self.mtc.test_rename_mgr_FileReplicaAlreadyExists_single_lfn()

    @raises(exception.FileReplicaAlreadyExists)
    def test_rename_mgr_FileReplicaAlreadyExists_single_pfn(self):
        """GFAL2 (RSE/PROTOCOLS): Rename a single file on storage using PFN (FileReplicaAlreadyExists)"""
        self.mtc.test_rename_mgr_FileReplicaAlreadyExists_single_pfn()

    @raises(exception.SourceNotFound)
    def test_rename_mgr_SourceNotFound_multi(self):
        """GFAL2 (RSE/PROTOCOLS): Rename multiple files on storage (SourceNotFound)"""
        self.mtc.test_rename_mgr_SourceNotFound_multi()

    @raises(exception.SourceNotFound)
    def test_rename_mgr_SourceNotFound_single_lfn(self):
        """GFAL2 (RSE/PROTOCOLS): Rename a single file on storage using LFN (SourceNotFound)"""
        self.mtc.test_rename_mgr_SourceNotFound_single_lfn()

    @raises(exception.SourceNotFound)
    def test_rename_mgr_SourceNotFound_single_pfn(self):
        """GFAL2 (RSE/PROTOCOLS): Rename a single file on storage using PFN (SourceNotFound)"""
        self.mtc.test_rename_mgr_SourceNotFound_single_pfn()

    def test_change_scope_mgr_ok_single_lfn(self):
        """GFAL2 (RSE/PROTOCOLS): Change the scope of a single file on storage using LFN (Success)"""
        self.mtc.test_change_scope_mgr_ok_single_lfn()

    def test_change_scope_mgr_ok_single_pfn(self):
        """GFAL2 (RSE/PROTOCOLS): Change the scope of a single file on storage using PFN (Success)"""
        self.mtc.test_change_scope_mgr_ok_single_pfn()
