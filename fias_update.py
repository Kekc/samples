#-*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings

import urllib2
from rarfile import RarFile
from suds.client import Client
from StringIO import StringIO
from lxml import etree


from light.models import AddressObj, House, FiasUpdateInfo


class Command(BaseCommand):


    help = u'downloads latest fias update and installs it to DB.'


    def handle(self, *args, **options):
        update_flag = True

        try:
            latest_update = FiasUpdateInfo.objects.latest('create_ts')
        except FiasUpdateInfo.DoesNotExist:
            latest_update = None

        fias_soap = Client(settings.FIAS_URL)

        latest_soap = fias_soap.service.GetLastDownloadFileInfo()

        version = latest_soap.VersionId

        if latest_update:
            if int(version) <= int(latest_update.version):
                update_flag = False


        if update_flag:
            xurl = latest_soap.FiasDeltaXmlUrl
            delta_file = urllib2.urlopen(xurl)
            input_file = StringIO(delta_file.read())
            new_update = FiasUpdateInfo(version=version)
            new_update.textversion = latest_soap.TextVersion.encode('utf8')
            new_update.delta_url = latest_soap.FiasDeltaXmlUrl
            new_update.delta_file.save('fias_update_%s.rar' % version, ContentFile(input_file.getvalue()), save=False)

            new_update.save()

            #unpack, get xml, write to DB

            rar_file = RarFile(new_update.delta_file.path)

            update_file_addr = None
            update_file_house = None
            for packed_file in rar_file.namelist():
                if packed_file.find('_ADDROBJ_') >= 0:
                    update_file_addr = packed_file
                if packed_file.find('_HOUSE_') >= 0:
                    update_file_house = packed_file

            #AddressObj
            if not update_file_addr:
                xml_string_addr = rar_file.read(update_file_addr)

                xml_tree_addr = etree.fromstring(xml_string_addr)
                update_items_addr = xml_tree_addr.getchildren()
                if update_items_addr and update_items_addr[0].keys():
                    fields_addr = update_items_addr[0].keys()
                    update_length_addr = len(update_items_addr)

                    for counter_addr, update_item_addr in enumerate(update_items_addr):
                        new_addrobj = AddressObj()
                        for field_addr in fields_addr:
                            setattr(new_addrobj, field_addr, update_item_addr.get(field_addr))

                        new_addrobj.save()
                        print u'%s Address objects left' % (update_length_addr-counter_addr)
                else:
                    print u'Wrong format of Address update file'
            else:
                print u'AddressObj file not found in the update'

            #House
            if update_file_house:
                xml_string_house = rar_file.read(update_file_house)

                xml_tree_house = etree.fromstring(xml_string_house)
                update_items_house = xml_tree_house.getchildren()
                if update_items_house and update_items_house[0].keys():
                    fields_house = update_items_house[0].keys()
                    update_length_house = len(update_items_house)

                    for counter_house, update_item_house in enumerate(update_items_house):
                        new_house = House()
                        for field_house in fields_house:
                            setattr(new_house, field_house, update_item_house.get(field_house))

                        new_house.save()
                        print u'%s House objects left' % (update_length_house-counter_house)
                else:
                    print u'Wrong format of House update file'
            else:
                print u'House file not found in the update'

            print u'Updated successfully'

        else:
            print u'No new updates found'

