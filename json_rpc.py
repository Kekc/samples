#-*- coding: utf-8 -*-

u"""Функции для создания объекта и присвоения регистрационного номера из других приложений.
"""

from jsonrpc import jsonrpc_method
from xml_checker.models import CheckerUser, Organisation, Passport, PassportMeta
from xml_checker.utils import xml_from_lite, Xml_object
from django.contrib.auth.models import Group
from json_rpc.utils import rpc_error_email

import json
import os

from django.conf import settings
from lxml import etree

@jsonrpc_method('json_rpc.create_object')
def create_object(request, new_object):
    try:
        try:
            user = CheckerUser.objects.get(username=new_object['owner'])
        except CheckerUser.DoesNotExist:
            user = None
        try:
            org = Organisation.objects.get(global_id=new_object['inspector_global_id'])
        except Organisation.DoesNotExist:
            org = None
        if org and user:
            xml_file = open(new_object['xml_path'])
            try:
                passport = Passport.objects.get(epmlite_org_id=new_object['epmlite_org_id'], is_delete=False)
            except Passport.DoesNotExist:
                passport = Passport(user=user, org=org, epmlite_org_id=new_object['epmlite_org_id'])
                passport.save()
                passport_meta = PassportMeta(passport=passport)
                passport_meta.save()
            loaded_passport = xml_from_lite(passport=passport, xml_file=xml_file, file_from_disk=True)
            if loaded_passport:
                if new_object['performer']:
                    try:
                        performer = CheckerUser.objects.get(username=new_object['performer'])
                    except CheckerUser.DoesNotExist:
                        performer = None
                else:
                    performer = None
                if performer:
                    loaded_passport.performers.add(performer)

                loaded_passport.save()
    except Exception, e:
        rpc_error_email('Checker: create_object', new_object, e)


@jsonrpc_method('json_rpc.set_sro_number')
def set_sro_number(request, org_id, object_dict):
    try:
        passport = Passport.objects.get(pk=org_id)
        passport_meta = passport.passportmeta_passport_set
        passport_meta.sro_number = object_dict['sro_number']

        xml_file = passport.file_passport_set.get(type=1, is_delete=False).epmfile
        xml_object = Xml_object(xml_file)
        xml_object.xml.xpath('//EnergyPassport/EnergyPassportTitle')[0].attrib['RegistrationNumber'] = object_dict['sro_number']

        xml_file_text = etree.tostring(xml_object.xml, pretty_print=True, encoding='utf-8', method='xml', xml_declaration=True)                               # записываем

        if len(xml_file_text) > 0:
            _file = open(xml_file._get_path(), "w")
            _file.writelines(xml_file_text)             # файл обратно
            _file.close()                                                           #

        passport_dir = u'%s/checker/%s/' % (settings.SHARED_DIR, passport.id)

        xml_file_name = u'%s' % passport.file_passport_set.get(type=1, is_delete=False).name
        xml_path = u'%s%s' % (passport_dir, xml_file_name)

        if not os.path.exists(passport_dir):
            os.makedirs(passport_dir)

        if len(xml_file_text) > 0:
            with open(xml_path, 'w') as xml_file:
                xml_file.write(xml_file_text)

    except Exception, e:
        data = json.dumps(org_id) + json.dumps(object_dict)
        rpc_error_email('Checker: set_sro_number', data, e)