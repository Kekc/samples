u"""Пример расчета форм энергопаспорта.
"""

class Form4(object):

    def __init__(self, org):
        self.org = org
        self.passport = org.passport_org_set
        self.base_year = self.passport.base_year
        self.year_aliases = ['prevYear4', 'prevYear3', 'prevYear2', 'prevYear1', 'baseYear']

    def del_year(self, reason):
        split_reason = [item for item in reason.split(' ') if not item.isdigit()]
        return u' '.join(split_reason)

    def get_data(self):
        data = {}
        data['base_year'] = str(self.base_year)
        consum_items = Form4Data.objects.filter(org=self.org)

        for item in consum_items:
            res_alias = item.resource_alias.replace('a4.', '')
            data[res_alias] = {}
            for year in self.year_aliases:
                data[res_alias][year] = float(getattr(item, year) or 0)

            empty_reasons = EmptyConsum.objects.filter(org=self.org, empty=True, resource_alias=item.resource_alias)
            text_reasons = empty_reasons.values('reason').distinct()
            res_note = u''
            for reason in text_reasons:
                empty_items = empty_reasons.filter(reason=reason['reason']).values('year')
                empty_years = ', '.join([str(empty_item['year']) for empty_item in empty_items])
                res_note += u'Потребление в %s отсутствует, т.к. %s ' % (empty_years, reason['reason'].lower())


            deltas = ConsumDelta.objects.filter(org=self.org, resource_alias=item.resource_alias, is_delete=False).exclude(delta__lt=5, delta__gt=-5)
            # res_delta = u' '.join([delta.reason for delta in deltas])
            res_delta = []
            deltas_dict = {}
            for delta in deltas:
                delta_y = self.del_year(delta.reason)
                if not delta_y in deltas_dict:
                    deltas_dict[delta_y] = []
                    deltas_dict[delta_y].append(str(delta.year))
                else:
                    deltas_dict[delta_y].append(str(delta.year))

            for delta_reason, delta_years in deltas_dict.iteritems():
                years_str = u' %s ' % u', '.join(delta_years)
                real_delta = delta_reason.replace(u' г. ', years_str )
                res_delta.append(real_delta)


            data[res_alias]['note'] = res_note
            data[res_alias]['reason'] = u' '.join(res_delta)

        return data

class Form5(object):

    def __init__(self, org):
        self.org = org
        self.passport = org.passport_org_set
        self.base_year = self.passport.base_year

        self.year_aliases_dict = {
            'prevYear4': self.base_year - 4,
            'prevYear3': self.base_year - 3,
            'prevYear2': self.base_year - 2,
            'prevYear1': self.base_year - 1,
            'baseYear': self.base_year,
        }
        self.future_year_aliases = ['postYear1', 'postYear2', 'postYear3', 'postYear4', 'postYear5']

    def get_data(self):
        data = {}
        data['comments'] = []
        data['base_year'] = str(self.base_year)

        data['incoming'] = {}
        data['incoming']['outsource'] = {}
        data['incoming']['insource'] = {}

        data['outgoing'] = {}
        data['outgoing']['techout'] = {}
        data['outgoing']['unrationalloss'] = {}
        data['outgoing']['realloss'] = {}

        electro_resource = Resource.objects.filter(alias='electro')
        try:
            electro_checked = ConsumRes.objects.get(org=self.org, resource__alias='electro')
        except ConsumRes.DoesNotExist:
            electro_checked = None

        if electro_checked and electro_checked.checked:
            for year_alias, year_value in self.year_aliases_dict.iteritems():
                try:
                    electro_consum = ConsumData.objects.get(consumres=electro_checked, year=year_value, checked=True)
                except ConsumData.DoesNotExist:
                    electro_consum = None
                if electro_consum:
                    data['incoming']['outsource'][year_alias] = electro_consum.natural
                else:
                    data['incoming']['outsource'][year_alias] = 0

        else:
            for year_alias in self.year_aliases_dict.iterkeys():
                data['incoming']['outsource'][year_alias] = 0

        try:
            electro_recovery_checked = ConsumRes.objects.get(org=self.org, resource__alias='electro_recovery')
        except ConsumRes.DoesNotExist:
            electro_recovery_checked = None

        if electro_recovery_checked and electro_recovery_checked.checked:
            for year_alias, year_value in self.year_aliases_dict.iteritems():
                try:
                    electro_consum = ConsumData.objects.get(consumres=electro_recovery_checked, year=year_value, checked=True)
                except ConsumData.DoesNotExist:
                    electro_consum = None
                if electro_consum:
                    data['incoming']['insource'][year_alias] = electro_consum.natural
                else:
                    data['incoming']['insource'][year_alias] = 0
        else:
            for year_alias in self.year_aliases_dict.iterkeys():
                data['incoming']['insource'][year_alias] = 0




        for year_alias in self.year_aliases_dict.iterkeys():
            data['incoming'][year_alias] = data['incoming']['outsource'][year_alias] + data['incoming']['insource'][year_alias]
            data['outgoing'][year_alias] = data['incoming'][year_alias]
            data['outgoing']['techout'][year_alias] = data['incoming'][year_alias]

            data['outgoing']['unrationalloss'][year_alias] = 0
            data['outgoing']['realloss'][year_alias] = 0

        # Эффект от мероприятий в базовом году
        actions = Action.objects.filter(org=self.org, resource=electro_resource,
            implementation_year__isnull=False, implementation_quarter__isnull=False, is_delete=False, is_active=True)
        action_effect = 0
        for action in actions:
            action_effect += round(action.natural, 2)


        data['outgoing']['unrationalloss']['baseYear'] = action_effect
        data['outgoing']['realloss']['baseYear'] = action_effect
        data['outgoing']['techout']['baseYear'] = data['outgoing']['techout']['baseYear'] - action_effect

        #future years
        # Эффект от мероприятий раскладываем на прогнозные года
        action_spread_effect = {
            'postYear1': 0,
            'postYear2': 0,
            'postYear3': 0,
            'postYear4': 0,
            'postYear5': 0
        }
        saved_effect = 0

        for action in actions:
            spread_effect = action.get_effect()
            for year_alias in action_spread_effect.keys():

                action_spread_effect[year_alias] += spread_effect[year_alias]

        for year_alias in self.future_year_aliases:

            data['outgoing']['techout'][year_alias] = data['outgoing']['techout']['baseYear']

            saved_effect = round(saved_effect+action_spread_effect[year_alias], 2)

            data['outgoing']['unrationalloss'][year_alias] = round(data['outgoing']['unrationalloss']['baseYear'] - saved_effect, 2)
            data['outgoing']['realloss'][year_alias] = data['outgoing']['unrationalloss'][year_alias]

            data['outgoing'][year_alias] = data['outgoing']['techout'][year_alias] + data['outgoing']['unrationalloss'][year_alias]

            data['incoming'][year_alias] = data['outgoing'][year_alias]
            if data['incoming']['baseYear']:
                data['incoming']['insource'][year_alias] = (data['incoming']['insource']['baseYear']/data['incoming']['baseYear']) * data['incoming'][year_alias]
            else:
                data['incoming']['insource'][year_alias] = 0
            data['incoming']['outsource'][year_alias] = data['incoming'][year_alias] - data['incoming']['insource'][year_alias]


        #comments
        form_filled = False
        for year_alias in self.year_aliases_dict.iterkeys():
            if data['incoming'][year_alias] != 0:
                form_filled = True
                break

        if form_filled:
            data['comments'].append(u'''Расход электроэнергии за период, предшествующий базовому году,
                отнесен на статью "технологический расход", т.к. достоверные данные по другим статьям расхода отсутствуют.''')
            if not data['outgoing']['unrationalloss']['baseYear']:
                data['comments'].append(u'''Нерациональные потери отсутствуют,
                    так как потенциал энергосбережения по электрической энергии не выявлен.''')

        else:
            data['comments'].append(u'''Организация не потребляет электрическую энергию.''')



        if data['comments']:
            data['comments'][0] = u'Примечание: %s' % data['comments'][0]


        return data

