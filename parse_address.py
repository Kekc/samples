#-*- coding: utf-8 -*-

from django.core.management.base import BaseCommand

from django.conf import settings
from yandex_maps import api as yandex_api
from light.models import AddressObj, Address
from light.constants import *


class Command(BaseCommand):

    help = u'Usage:\n./manage.py parse_address \n Parsing address from string and saving it to valid FIAS object'

    def handle(self, *args, **options):

        city_levels = [1, 2, 3, 4, 5, 6]
        street_levels = [7, 90, 91]

        region_cities = [u'Москва', u'Санкт-Петербург']

        address_examples = [
            u'129515, Москва, ул. Академика Королева, д. 4, корп. 4',
            u'625016, Тюмень, улица Логунова, 6, 72',
            u'117036, Москва, пр. Черемушкинский, д. 5',
            u'614077, Пермский, Пермь, б-р Гагарина, д. 60 Б',
            u'236029, Калининград, ул. Беломорская, 23, кв. 2',
            u'117119, Москва, переулок Лефортовский, 12/50, 1',
            u'353411, Краснодарский край, Анапский район, с. Супсех, ул. Мира, д. 7',
            u'603022, г Нижний Новгород, ул Малая Ямская, д 78, А',
            u'362007, г Владикавказ, ул Кутузова, д 8',
            u'450106, Уфа, ул. Степана Кувыкина, 25/1',
            u'194100, Санкт-Петербург, ул. Кантемировская, 12, лит. А, пом. 41-Н',
            u'115093, Москва, переулок Партийный, 1, корп. 57, стр. 3',
            u'630028, Новосибирская обл., Новосибирск, Нижегородская ул., 280',
            u'636210, Томская область, Бакчарский район, п Плотниково, ул Трактовая, д 18',
            u'429282, Чувашская Республика, Янтиковский р-н, с. Яншихово-Норваши, ул. Ленина, 4',
            u'123100, Москва, Шмитовский проезд, 13/6, 1',
            u'680006, Г ХАБАРОВСК, УЛ ЦЕНТРАЛЬНАЯ, Д 10, ОФ 63',
        ]


        for address_string in address_examples:
            print u'\n\n %s' % address_string

            address_vals = address_string.split(',')
            index = address_vals[0].strip()
            address_iter_vals = address_vals[1:]

            housenum = []

            region_name = u''
            city_name = u''
            street_name = u''

            kladr_code = u''
            city_code = u''
            street_code = u''
            street_aoguid = u''

            city_flag = False
            street_flag = False

            for address_iter_val in address_iter_vals:
                print u'iter val   ', address_iter_val
                item_addr_objs = []

                #replacing all socr names
                address_iter_val = address_iter_val.strip().lower()
                address_iter_val = address_iter_val.replace(u'.', u'')
                for replace_item in ADDRESS_SOCRNAMES + ADDRESS_SCNAMES:
                    replace_item_start_low = u'%s ' % replace_item.lower()
                    replace_item_start = u'%s ' % replace_item
                    replace_item_end_low = u' %s' % replace_item.lower()
                    replace_item_end = u' %s' % replace_item
                    if address_iter_val.startswith(replace_item_start):
                        address_iter_val = address_iter_val.replace(replace_item_start, u'')
                    elif address_iter_val.startswith(replace_item_start_low):
                        address_iter_val = address_iter_val.replace(replace_item_start_low, u'')
                    if address_iter_val.endswith(replace_item_end):
                        address_iter_val = address_iter_val.replace(replace_item_end, u'')
                    elif address_iter_val.endswith(replace_item_end_low):
                        address_iter_val = address_iter_val.replace(replace_item_end_low, u'')


                address_item = address_iter_val.strip()

                #finding city_name
                if not city_name:
                    adr_objs = AddressObj.objects.filter(FORMALNAME=address_item, AOLEVEL__in=city_levels, ACTSTATUS=1)
                    if not adr_objs and address_item not in region_cities:
                        adr_objs = AddressObj.objects.filter(FORMALNAME__contains=address_item, AOLEVEL__in=city_levels, ACTSTATUS=1)
                    if kladr_code:
                        adr_objs = adr_objs.filter(CODE__startswith=kladr_code).order_by('AOLEVEL')
                    else:
                        adr_objs = adr_objs.order_by('AOLEVEL')
                    if adr_objs:
                        adr_obj = adr_objs[0]
                        print address_item, adr_obj.AOLEVEL, adr_obj.FORMALNAME, adr_obj.CITYCODE, adr_obj.PLACECODE
                        if adr_obj.CITYCODE != u'000' or adr_obj.PLACECODE != u'000' or adr_obj.FORMALNAME in region_cities:
                            city_name = u'%s %s' % (adr_obj.FORMALNAME, adr_obj.SHORTNAME)
                            city_code = adr_obj.CODE
                            region_name = adr_obj.parse_fias()['region']
                        kladr_full_code =  adr_obj.CODE
                        kladr_list1 = list(kladr_full_code)
                        kladr_list2 = []
                        kladr_list1.reverse()
                        kladr_flag = False
                        for item in kladr_list1:
                            if item != u'0':
                                kladr_flag = True
                            if kladr_flag:
                                kladr_list2.append(item)
                        kladr_list2.reverse()
                        kladr_code = ''.join(kladr_list2)
                        #if we get city_name immediatly start next iteration
                        continue



                #finding street name
                if not street_name and city_name:
                    adr_objs = AddressObj.objects.filter(FORMALNAME=address_item, AOLEVEL__in=street_levels, ACTSTATUS=1, CODE__startswith=kladr_code).order_by('AOLEVEL')
                    if not adr_objs:
                        adr_objs = AddressObj.objects.filter(FORMALNAME__contains=address_item, AOLEVEL__in=street_levels, ACTSTATUS=1, CODE__startswith=kladr_code).order_by('AOLEVEL')
                    if adr_objs:
                        adr_obj = adr_objs[0]
                        #print adr_obj.AOLEVEL, adr_obj.FORMALNAME, adr_obj.STREETCODE
                        street_name = u'%s %s' % (adr_obj.FORMALNAME, adr_obj.SHORTNAME)
                        street_code = adr_obj.CODE
                        street_aoguid = adr_obj.AOGUID
                        continue

                #append everything after street_name to housenum
                if street_name:
                    housenum.append(address_item)

            # empty city for Москва Санкт-Петербург
            if city_name in region_cities:
                city_name = u''
                city_code = u''

            # arrange house number and office number
            office_shorts = [u'кв', u'квартира', u'оф', u'офис']

            if housenum:
                if len(housenum) == 1:
                    house_number = u'%s~~' % housenum[0]
                    office_number = u''
                elif len(housenum) == 2:
                    house_number = u'%s~%s~' % (housenum[0], housenum[1])
                    office_number = u''
                    for office_short in office_shorts:
                        if office_short in housenum[1]:
                            house_number = u'%s~~' % housenum[0]
                            office_number = housenum[1].replace(office_short, u'')
                            break

                else:
                    house_number = u'%s~%s~' % (housenum[0], housenum[1])
                    office_number = '~'.join(housenum[2:])
            else:
                house_number = u''
                office_number = u''

            # testing xml template
            xml_template = u'''
                <Region>%s</Region>
                <PostCode>%s</PostCode>
                <City Code="%s">%s</City>
                <Street Code="%s">%s</Street>
                <Building>%s</Building>
                <Office>%s</Office>
            '''
            print xml_template % (region_name, index, city_code, city_name, street_code, street_name, house_number, office_number)

            # saving to Address() with plain string and coords
            address_string = u'%s, %s, %s' % (region_name, city_name, street_name)
            address_to_save = Address()

            address_to_save.address_type = 1
            address_to_save.aoguid = street_aoguid
            address_to_save.code = street_code
            address_to_save.postal_code = index
            address_to_save.housenum = house_number
            address_to_save.officenum = office_number
            address_to_save.address = address_string

            address_to_save.save()

            geo = yandex_api.geocode(settings.YANDEX_MAPS_API_KEY, address_to_save.__unicode__())
            address_to_save.latitude = geo[1]
            address_to_save.longitude = geo[0]

            address_to_save.save()

            return address_to_save

