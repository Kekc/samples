class Address(models.Model):
    u"""Наша модель адреса для работы с объектами ФИАС
    """
    
    EXT_FIELDS = [
        'aoguid',
        'code',
        'postal_code',
        'address',
        'housenum',
    ]

    TYPE_ADDR = (
        (1, u'Юридический'),
        (2, u'Фактический'),
        (3, u'Почтовый'),
    )
    #plain_text = models.CharField(max_length=255, verbose_name=u'Адрес')
    address_type = models.IntegerField(default=1, verbose_name=u'Тип адреса')
    aoguid = models.CharField(max_length=50, verbose_name=u'Код ФИАС')
    code = models.CharField(max_length=50, verbose_name=u'КЛАДР код')
    postal_code = models.CharField(max_length=6, verbose_name=u'Почтовый индекс')
    housenum = models.CharField(max_length=24, verbose_name=u'Номер дома', blank=True)
    officenum = models.CharField(max_length=16, verbose_name=u'Номер офиса', blank=True)
    address = models.CharField(max_length=250, verbose_name=u'Адрес (без номера дома)')

    latitude = models.FloatField(verbose_name=u'Широта', blank=True, null=True)
    longitude = models.FloatField(verbose_name=u'Долгота', blank=True, null=True)

    edited_region = models.CharField(max_length=200, verbose_name=u'Отредактированный регион', blank=True)
    edited_city = models.CharField(max_length=200, verbose_name=u'Отредактированный город', blank=True)
    edited_street = models.CharField(max_length=200, verbose_name=u'Отредактированная улица', blank=True)
    edited_code = models.CharField(max_length=200, verbose_name=u'Отредактированный код', blank=True)

    def __unicode__(self):
        address_string = u'%s, ' % self.postal_code
        if self.edited_region or self.edited_city or self.edited_street:
            address_string += u'%s, %s, %s' % (self.edited_region, self.edited_city, self.edited_street)
        
        elif self.address:
            address_string += self.address
        
        if self.housenum:
            address_string +=  u', %s' % self.housenum
            if self.officenum:
                address_string +=  u', %s' % self.officenum
        return address_string

    def search_nearest_city(self, base='norm'):

        latitude = self.latitude
        longitude = self.longitude
        lens = {}
        if latitude and longitude:
            if base == 'norm':
                cities = CatTermOutOx.objects.filter(latitude__isnull=False, longitude__isnull=False).values('gor', 'latitude', 'longitude').distinct()
                for city in cities:
                    lens[float(pow(pow(latitude-city['latitude'],2)+pow(longitude-city['longitude'],2),0.5))]=city['gor']
            elif base == 'fact':
                cities = ClimatYearFact.objects.values('city', 'latitude','longitude').distinct()
                for city in cities:
                    lens[float(pow(pow(latitude-city['latitude'],2)+pow(longitude-city['longitude'],2),0.5))]=city['city']
            else:
                cities = []
                return None


            k = lens.keys()
            k.sort()

            return lens[k[0]]
        else:
            return None


    def parse_fias(self, clean=False):
        parsed_address = {}
        if AddressObj.objects.filter(AOGUID=self.aoguid):
            fias_object = AddressObj.objects.filter(AOGUID=self.aoguid)[0]

            def fias_search(fias_object, parsed_address, clean=False):
                level = AddressObj.AOLEVEL_DICT[fias_object.AOLEVEL]
                if clean:
                    parsed_address[level] = u'%s' % fias_object.FORMALNAME
                else:
                    parsed_address[level] = u'%s %s' % (fias_object.FORMALNAME, fias_object.SHORTNAME)
                if fias_object.PARENTGUID:
                    parent_object = AddressObj.objects.filter(AOGUID=fias_object.PARENTGUID)[0]
                    fias_search(parent_object, parsed_address, clean)

            fias_search(fias_object, parsed_address, clean=clean)

        return parsed_address