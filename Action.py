class Action(models.Model):
    u"""Энергосберегающие мероприятия. Расчет эффекта, сроков внедрения и окупаемости мероприятий.
    """

    EFFECT_TYPES = (
        (1, u'Отопление и вентиляция'),
        (2, u'ГВС'),
    )
    ACTION_TYPES = (
        (1, u'Организационное'),
        (2, u'Сберегающее'),
    )
    ACTION_PAYBACK = (
        (0, u'Не указано'),
        (1, u'Краткосрочное'),
        (2, u'Среднесрочное'),
        (3, u'Долгосрочное'),
    )

    org       = models.ForeignKey(Organisation,related_name='action_org_set',verbose_name=u'Организация')
    building  = models.ForeignKey(Building,related_name='action_building_set',verbose_name=u'Здание', blank=True, null=True)

    alias     = models.CharField(max_length=40, blank=True, null=True, verbose_name=u'Алиас')
    name      = models.TextField(verbose_name=u'Название')
    cost      = models.FloatField(blank=True, null=True, verbose_name=u'Затраты')
    effect    = models.FloatField(blank=True, null=True, verbose_name=u'Денежный эффект')
    unit      = models.CharField(max_length=50,  null=True, blank=True, verbose_name=u'Единицы измерения')
    natural   = models.FloatField(blank=True, null=True, verbose_name=u'Натуральный эффект')
    recoup    = models.FloatField(blank=True, null=True, verbose_name=u'Значение срока окупаемости')

    payback = models.IntegerField(choices=ACTION_PAYBACK, blank=True, verbose_name=u'Срок окупаемости мероприятия', default=0)

    resource  = models.ForeignKey(Resource, related_name='action_resource_set', blank=True, null=True, verbose_name=u'Ресурс')

    implementation_year = models.IntegerField(verbose_name=u'Срок внедрения год', blank=True, null=True)
    implementation_quarter = models.IntegerField(verbose_name=u'Срок внедрения квартал', blank=True, null=True)

    heat_effect_type = models.IntegerField(choices=EFFECT_TYPES, verbose_name=u'Адрес эффекта по теплу', blank=True, null=True)
    heat_originally = models.IntegerField(verbose_name=u'Изначально тепло', blank=True, default=0)

    is_active = models.BooleanField(default=True,verbose_name=u'Активен?')
    is_delete = models.BooleanField(default=False,verbose_name=u'Удален?')
    create_ts = models.DateTimeField(verbose_name=u'Дата создания', auto_now_add=True)
    mod_ts    = models.DateTimeField(verbose_name=u'Дата изменения', auto_now=True)

    def __unicode__(self):
        return u'%s %s %s' % (self.org, self.resource, self.natural)

    def recoupment(self):
        if self.effect:
            try:
                self.recoup = round(self.cost/self.effect, 2)
            except:
                self.recoup = 0
        else:
            self.recoup = 0

        if self.recoup:
            if self.recoup <= 2:
                self.payback = 1
            elif self.recoup > 2 and self.recoup <=5:
                self.payback = 2
            elif self.recoup > 5:
                self.payback=3
        else:
            self.payback = 0

    def get_kpd(self):
        boilers = Boiler.objects.filter(org=self.org, resources=self.resource, is_delete=False)
        kpd = 0
        if boilers:
            for boiler in boilers:
                kpd += boiler.get_kpd()
            kpd /= len(boilers)
        if kpd:
            return kpd


    def get_effect(self, unit=None, kpd=None):
        result = {
            'postYear1': 0,
            'postYear2': 0,
            'postYear3': 0,
            'postYear4': 0,
            'postYear5': 0
        }
        if self.resource and self.natural and self.implementation_year and self.implementation_quarter:
            base_year = self.org.passport_org_set.base_year
            years_dict = {
                base_year + 1: 'postYear1',
                base_year + 2: 'postYear2',
                base_year + 3: 'postYear3',
                base_year + 4: 'postYear4',
                base_year + 5: 'postYear5'
            }

            if unit == 'tut':
                natural = self.natural * TUT_COEFF[self.resource.alias][self.unit]
            elif unit == 'gcal':
                if self.heat_effect_type in [1,2]:
                    kpd = self.get_kpd() or 1
                else:
                    kpd = 1
                natural = (kpd * self.natural * TUT_COEFF[self.resource.alias][self.unit]) / 0.1486
            else:
                natural = self.natural

            effect = natural / 4.0

            quarter = self.implementation_quarter

            start_year = years_dict[self.implementation_year]
            next_year = years_dict[self.implementation_year + 1]

            start_year_effect = round((abs(quarter-4)+1) * effect, 2)
            next_year_effect = round(natural - start_year_effect, 2)

            result[start_year] = start_year_effect
            result[next_year] = next_year_effect

        return result

    def get_date(self):
        quarters = {
            1: u'01-01',
            2: u'04-01',
            3: u'07-01',
            4: u'10-01',
        }
        if self.implementation_quarter and self.implementation_year:
            return u'%s-%s' % (self.implementation_year, quarters[self.implementation_quarter])
        else:
            # return u'1900-01-01'
            self.implementation_year = self.org.passport_org_set.base_year + ACTION_DATES_BY_ALIAS[self.alias]['add_year']
            self.implementation_quarter = ACTION_DATES_BY_ALIAS[self.alias]['quarter']
            self.save()
            return u'%s-%s' % (self.implementation_year, quarters[self.implementation_quarter])

            