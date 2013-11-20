#-*- coding: utf-8 -*-
u"""Логические проверки пользовательских данных. Собираются в формате удобном для того, чтобы отдавать в ExtJS.
"""

from light.models import *


class LogicChecker(object):

    def __init__(self, org):
        self.org = org
        self.passport = Passport.objects.get(org=org)
        self.base_year = self.passport.base_year
        self.prev_years = self.passport.get_prev_years()
        self.prev_aliases = self.passport.get_prev_aliases()
        self.buildings = Building.objects.filter(org=org, is_delete=False)

    def consum_deltas(self):
        temp_data = []
        deltas = ConsumDelta.objects.filter(org=self.org, is_delete=False, reason=u'').exclude(delta__lt=10, delta__gt=-10)
        resource_year = {}
        error_data = []
        for delta in deltas:
            if delta.resource not in resource_year:
                resource_year[delta.resource] = []
            resource_year[delta.resource].append(str(delta.year))
        for res, years in resource_year.iteritems():
            error = u''
            error += u'%s в %s' % (res, u', '.join(years))
            error += u' г.' if len(years) == 1 else u' гг.'
            error_data.append(error)
        if error_data:
            temp_data.append({
                'form':  u'Потребление',
                'table': u'Колебания потребления',
                'error': u'Не заполнены причины колебаний потребления по %s' % (' '.join(error_data))
            })
        return temp_data

    def empty_consums(self):
        temp_data = []
        items = EmptyConsum.objects.filter(org=self.org, is_delete=False, empty=True, reason=u'')
        resource_year = {}
        error_data = []
        for item in items:
            if item.resource not in resource_year:
                resource_year[item.resource] = []
            resource_year[item.resource].append(str(item.year))
        for res, years in resource_year.iteritems():
            error = u''
            error += u'%s в %s' % (res, u', '.join(years))
            error += u' г.' if len(years) == 1 else u' гг.'
            error_data.append(error)
        if error_data:
            temp_data.append({
                'form':  u'Потребление',
                'table': u'Отсутствие данных по потреблению',
                'error': u'Не заполнены причины отсутствия данных по потребления по %s' % (' '.join(error_data))
            })
        return temp_data

    def auto_fuel(self):
        temp_data = []
        fuel_dict = {
            'petrol': [u'Бензин А-76', u'Бензин А-80', u'Бензин Аи-92', u'Бензин Аи-93', u'Бензин Аи-95', u'Бензин Аи-98',],
            'diesel': [u'Диз. топливо'],
            'motor_gas': [u'Пропан', u'Метан'],
            'liquid_gas': [u'Газ сжиженный'],
            'kerosene': [u'Керосин'],
        }

        for res, fuels in fuel_dict.items():
            consum_sum = 0
            fuel_sum = 0
            consum_name = Resource.objects.get(alias=res).name
            fuel_name = u'Бензин' if res == 'petrol' else ', '.join(fuels)

            try:
                consumres = ConsumRes.objects.get(org=self.org, resource__alias=res)
            except ConsumRes.DoesNotExist:
                consumres = None
            if consumres and consumres.checked:
                consum_data = ConsumData.objects.get(consumres=consumres, year=self.base_year)
                if consum_data.checked:
                    consum_sum = round(consum_data.natural / 1000.0, 2)

            cars = Car.objects.filter(org=self.org, is_delete=False, fuel_type__in=fuels)
            for car in cars:
                fuel_sum += round(car.fuel_m3 or car.fuel_l or 0, 2)

            if fuel_sum or consum_sum:
                if round(fuel_sum,2) != round(consum_sum,2):
                    temp_data.append({
                        'form':  u'Потребление и деятельность организации',
                        'table': u'Потребление %s, сведения о автотранспорте' % consum_name,
                        'error': u'Не сходиться потребление %s по факту потребления автотранспортом и по факту отчетного потребления за базовый год.' % res,
                        'comment': u'Сведения о автотранспорте и технике потребляющей моторное топливо, %s - %s тыс.л.,  Потребление, %s - %s тыс.л.' % (fuel_name, fuel_sum, consum_name, consum_sum)
                    })

        return temp_data

    def get_checked_resources(self):
        return ConsumRes.objects.filter(org=self.org, checked=True)

    def consum_year_sum(self, year, resource=None, target=None):
        sum = 0
        if not resource:
            checked_res = self.get_checked_resources()
        else:
            checked_res = ConsumRes.objects.filter(org=self.org, resource=resource, checked=True)
        for consumres in checked_res:
            try:
                consum_data = ConsumData.objects.get(consumres=consumres, year=year, checked=True)
            except ConsumData.DoesNotExist:
                consum_data = None
            if consum_data:
                if not target:
                    sum += round(consum_data.money * MONEY_COEFF[consum_data.money_unit], 2)
                elif target == 'natural':
                    sum += round(consum_data.natural * FORM4_COEFF[consumres.resource.alias][consum_data.natural_unit], 2)

        return sum

    def produciton_consum_compare(self):
        temp_data = []
        error_years = []
        comments = []
        try:
            production = OrgActivity.objects.get(org=self.org, name=2)
        except OrgActivity.DoesNotExist:
            production = None

        for alias, year in self.prev_aliases.items():
            consum_sum = self.consum_year_sum(year)
            if production:
                if getattr(production, alias) or consum_sum:
                    if getattr(production, alias) <= consum_sum:
                        error_years.append(str(year))
                        comments.append(u'%s г. - Сумма затрат на энергоресурсы: %s тыс. руб., Объем производства продукции: %s тыс. руб.' % (year, consum_sum, getattr(production, alias)))
            else:
                error_years.append(str(year))
                comments.append(u'%s г. - Сумма затрат на энергоресурсы: %s тыс. руб., Объем производства продукции: %s тыс. руб.' % (year, consum_sum, u'*Не заполнен*'))

        if error_years:
            error_string = u', '.join(error_years)
            error_string += u' г' if len(error_years) == 1 else u' гг'
            temp_data.append({
                'form':  u'Потребление и деятельность организации',
                'table': u'Потребление - сумма денежных выражений по всем Тэр за 1 год; Объем производства продукции',
                'error': u'Неверно указан объем производства продукции в денежном выражении за %s.' % error_string,
                'comment': u'; '.join(comments)
            })

        return temp_data

    def light_consum_compare(self):
        temp_data = []
        lights = Light.objects.filter(org=self.org, is_delete=False)
        light_sum = 0
        for light in lights:
            power = float(light.power or 0)
            count = light.count or 0
            hours = light.hours or 0
            days = light.days or 0
            light_sum += round(0.9 * power * count * hours * days * (1.0/10**6), 2)
        electro = Resource.objects.get(alias='electro')
        consum_sum = self.consum_year_sum(self.base_year, resource=electro, target='natural')

        if consum_sum:
            percent = round(100 * (light_sum/consum_sum), 2)
        else:
            percent = 100
        if percent >= 90:
            temp_data.append({
                'form':  u'Потребление, деятельность организации, опросники по каждому зданию',
                'table': u'Потребление электроэнергии за базовый год; Сведения по осветительному оборудованию',
                'error': u'Неверно указаны либо мощности осветительного оборудования, либо сведения о его времени работы в сутки и в год.',
                'comment': u'''Потребление электрической энергии за базовый год - %s тыс. кВт.ч.,
                     потребление осветительным оборудованием в организации - %s тыс. кВт.ч,
                     что составляет %s %% от потребления в год.
                     Потребление на освещение должно быть не более 85 %%
                     потребления электрической энергии в организации в год.''' % (consum_sum, light_sum, percent)
            })

        return temp_data

    def boiler_resource(self):
        temp_data = []
        comments = []
        checked_res = self.get_checked_resources()
        boiler_res = Resource.objects.filter(form4_alias__in=['a4.liquidfuel', 'a4.hardfuel'])
        checked_boiler_res = checked_res.filter(resource__in=boiler_res)
        if checked_boiler_res:
            for res in checked_boiler_res:
                boilers = Boiler.objects.filter(org=self.org, is_delete=False, resources=res.resource)
                if not boilers:
                    comments.append(res.resource.name)

        if comments:
            temp_data.append({
                'form':  u'Потребление и деятельность организации',
                'table': u'Потребление - котельно печное топливо; Деятельность организации - сведения о котельных',
                'error': u'Не заполнены сведения о котельных, потребляющих следующие виды топлива -  %s.' % u', '.join(comments),
                'comment': u''
            })

        return temp_data

    def building_volume(self, building, building_general):
        temp_data = []

        volume = building_general.volume
        area = building_general.area
        stage = building_general.stage
        if volume and area and stage:
            if volume < area*2:
                temp_data.append({
                    'form':  u'Опросники по каждому зданию',
                    'table': u'Суммарная площадь помещений, общий объем здания',
                    'error': u'Неверно указан общий объем, либо суммарная площадь помещений %s' % building.get_name(),
                    'comment': u'При указанной площади помещений объем не может быть меньше чем %s м3.' % (area*2)
                })
            if volume > area*stage*12:
                temp_data.append({
                    'form':  u'Опросники по каждому зданию',
                    'table': u'Суммарная площадь помещений, общий объем здания',
                    'error': u'Неверно указан общий объем, либо суммарная площадь помещений %s' % building.get_name(),
                    'comment': u'При указанной площади помещений объем не может быть меньше чем %s м3.' % (area*stage*12)
                })

        return temp_data

    def building_workers(self, building, building_general):
        temp_data = []

        workers_building = building_general.worker_count
        workers_org = OrgActivity.objects.get(org=self.org, name=1, is_delete=False).baseYear
        if workers_building and workers_org:
            if workers_building > workers_org:
                temp_data.append({
                    'form':  u'Деятельность организации, Опросники по каждому зданию',
                    'table': u'Опросники по каждому зданию: количество работников в сутки; Деятельность организации: среднегодовая численность работников в базовом году.',
                    'error': u'Неверно указано количество работников в сутки %s' % building.get_name(),
                    'comment': u'Среднегодовая численность работников в базовом году -  %s чел., работников в сутки в %s - %s чел.' % (workers_org, building.get_name(), workers_building)
                })

        return temp_data

    def building_wash(self, building, building_general):
        temp_data = []
        errors = []
        function = building_general.function
        if function and function.parent in WASHING_FUNCTIONS:
            if not building_general.consumer_count:
                errors.append(u'количество потребителей в сутки')
            if not building_general.toilet_count:
                errors.append(u'количество бачков всего')
            if not building_general.wash_count:
                errors.append(u'количество умывальников всего')
            if errors:
                temp_data.append({
                    'form':  u'Опросники по каждому зданию.',
                    'table': u'Опросники по каждому зданию.',
                    'error': u'Не заполнены необходимые сведения по %s - %s' % (', '.join(errors), building.get_name()),
                    'comment': u''
                })

        return temp_data

    def building_light(self, building, building_general):
        temp_data = []
        lights = Light.objects.filter(building=building, is_delete=False)
        function = building_general.function
        if function and function.parent not in LIGHT_FUNCTIONS:
            if not lights:
                temp_data.append({
                    'form':  u'Опросники по каждому зданию.',
                    'table': u'Опросники по каждому зданию.',
                    'error': u'Не заполены все необходимые сведения по %s - (сведения по осветительному оборудовании).' % (building.get_name()),
                    'comment': u''
                })

        return temp_data


    def get_data(self):
        data = []
        data += self.consum_deltas()
        data += self.empty_consums()
        data += self.auto_fuel()
        data += self.produciton_consum_compare()
        data += self.light_consum_compare()
        data += self.boiler_resource()

        for building in self.buildings:
            building_general = BuildingGeneral.objects.get(building=building)
            data += self.building_volume(building, building_general)
            data += self.building_workers(building, building_general)
            data += self.building_wash(building, building_general)
            data += self.building_light(building, building_general)

        return data


def leadin_building_check(org):
    errors = []
    buildings = org.building_org_set.filter(is_delete=False)

    try:
        electro_flag = ConsumRes.objects.get(org=org, resource__alias='electro', checked=True)
        electro_leadins = Leadin.objects.filter(org=org, resource__alias='electro', is_delete=False)
    except ConsumRes.DoesNotExist:
        electro_flag = False

    try:
        heat_flag = ConsumRes.objects.get(org=org, resource__alias='heat', checked=True)
        heat_leadins = Leadin.objects.filter(org=org, resource__alias='heat', is_delete=False)
    except ConsumRes.DoesNotExist:
        heat_flag = False

    try:
        water_flag = ConsumRes.objects.get(org=org, resource__alias='water', checked=True)
        water_leadins = Leadin.objects.filter(org=org, resource__alias='cold_water', is_delete=False)
    except ConsumRes.DoesNotExist:
        water_flag = False

    liquid_resources = Resource.objects.filter(form4_alias__contains='liquidfuel')
    liquid_flag = ConsumRes.objects.filter(org=org, resource__in=liquid_resources, checked=True)
    liquid_leadins = Leadin.objects.filter(org=org, resource__alias='liquid_fuel', is_delete=False)

    electro_buildings = []
    heat_buildings = []
    water_buildings = []
    liquid_buildings = []

    for building in buildings:
        ###### electro ######
        if electro_flag:
            if not electro_leadins.filter(buildings=building):
                try:
                    building_general = building.buildinggeneral_building_set
                except BuildingGeneral.DoesNotExist:
                    building_general = None
                if building_general:
                    building_electro_flag = False
                    if Cooker.objects.filter(building=building, is_delete=False):
                        building_electro_flag = True
                    if Light.objects.filter(building=building, is_delete=False):
                        building_electro_flag = True
                    if building_general.electro_heating:
                        building_electro_flag = True

                    if building_electro_flag:
                        electro_buildings.append(building.get_name_accusative())

        ###### heat ######
        if heat_flag:
            if not heat_leadins.filter(buildings=building):
                try:
                    building_general = building.buildinggeneral_building_set
                except BuildingGeneral.DoesNotExist:
                    building_general = None
                if building_general:
                    building_heat_flag = True
                    if not building_general.heating:
                        building_heat_flag = False
                    if building_general.electro_heating:
                        building_heat_flag = False
                    if Boiler.objects.filter(buildings=building, is_delete=False):
                        building_heat_flag = False

                    if building_heat_flag:
                        heat_buildings.append(building.get_name_accusative())

        ###### water cold ######
        if water_flag:
            if not water_leadins.filter(buildings=building):
                try:
                    building_general = building.buildinggeneral_building_set
                except BuildingGeneral.DoesNotExist:
                    building_general = None
                if building_general:
                    building_water_flag = False
                    if building_general.toilet_count:
                        building_water_flag = True
                    if building_general.wash_count:
                        building_water_flag = True
                    if building_general.wash_gvs_count:
                        building_water_flag = True
                    if building_general.shower_count:
                        building_water_flag = True
                    if SwimmingPool.objects.filter(building=building, is_delete=False):
                        building_water_flag = True

                    if building_water_flag:
                        water_buildings.append(building.get_name_accusative())
        ###### liquid fuel ######
        if liquid_flag:
            if not liquid_leadins.filter(buildings=building):
                try:
                    building_general = building.buildinggeneral_building_set
                except BuildingGeneral.DoesNotExist:
                    building_general = None
                if building_general:
                    building_liquid_flag = True

                    building_boilers = Boiler.objects.filter(buildings=building, is_delete=False)
                    if not building_boilers:
                        building_liquid_flag = False
                    else:
                        liquid_boilers = building_boilers.filter(resources__in=liquid_resources)
                        if not liquid_boilers:
                            building_liquid_flag = False

                    if building_liquid_flag:
                        liquid_buildings.append(building.get_name_accusative())

    if electro_buildings:
        electro_string = u'Не заполнены данные по узлам ввода электроэнергии в %s.' % (', '.join(electro_buildings))
        errors.append(electro_string)
    if heat_buildings:
        heat_string = u'Не заполнены данные по узлам ввода тепловой энергии в %s.' % (', '.join(heat_buildings))
        errors.append(heat_string)
    if water_buildings:
        water_string = u'Не заполнены данные по узлам ввода холодной воды в %s.' % (', '.join(water_buildings))
        errors.append(water_string)
    if liquid_buildings:
        liquid_string = u'Не заполнены данные по узлам ввода жидкого топлива в %s.' % (', '.join(liquid_buildings))
        errors.append(liquid_string)


    if errors:
        error_string = '<br/>'.join(errors)
        return error_string


def leadin_check(org):

    leadin_resources = [
        #'a4.water',
        'a4.heat',
        'a4.electro',
        'a4.naturegas',
        'a4.liquidfuel',
    ]

    transform_to_leadin = {
        'electro': ['electro'],
        'heat': ['heat'],
        'nature_gas': ['nature_gas'],
        'water': ['hot_water', 'cold_water'],
        'liquid_gas': ['liquid_fuel'],
        'kerosene': ['liquid_fuel'],
        'masut': ['liquid_fuel'],


    }

    try:
        water_source = WaterSource.objects.get(org=org)
    except WaterSource.DoesNotExist:
        water_source = None
    if water_source and water_source.plumbing:
        leadin_resources.append('a4.water')


    consums = ConsumRes.objects.filter(org=org, resource__form4_alias__in=leadin_resources, checked=True)
    if consums:
        error_res = []
        for consum in consums:
            if not Leadin.objects.filter(org=org, resource__alias__in=transform_to_leadin[consum.resource.alias], is_delete=False):
                error_res.extend(transform_to_leadin[consum.resource.alias])

        if error_res:
            res_join_list= []
            error_string = u'Обязательно должен быть хотя бы один оборудованный или необорудованный ввод по ресурсам '
            for item in error_res:
                res_join_list.append(Resource.objects.get(alias=item).name)
            error_string += ', '.join(res_join_list)
            return error_string


def orgactivity_check(org):
    base_year = Passport.objects.get(org=org).base_year

    VERBOSE_YEARS = {
        'prevYear4': base_year - 4,
        'prevYear3': base_year - 3,
        'prevYear2': base_year - 2,
        'prevYear1': base_year - 1,
        'baseYear': base_year,
    }

    error_string = u''
    if OrgActivity.objects.filter(org=org, is_delete=False):


        staff = OrgActivity.objects.get(org=org, name=1, is_delete=False)
        okp = OrgActivity.objects.get(org=org, name=4, is_delete=False)
        natural = OrgActivity.objects.get(org=org, name=3, is_delete=False)
        natural_flag = False
        data = []
        for field in OrgActivity.EXT_FLOAT_FIELDS:
            if getattr(staff, field) and not getattr(okp, field):
                data.append(str(VERBOSE_YEARS[field]))
            if getattr(natural, field):
                natural_flag = True



        if data:

            error_string += u'Не заполнен ОКП/ОКУН за '
            error_string += ', '.join(data)
            if len(data) == 1:
                error_string += u' г.'
            else:
                error_string += u' гг.'

            #return error_string

        if natural_flag and not getattr(natural, 'unit'):
            error_string += u'Не выбраны единицы измерения.'

    else:
        error_string = u'Не заполнена деятельность организации.'
    return error_string


def building_check(org):
    buildings = Building.objects.filter(org=org, is_delete=False)
    if not buildings:
        error_string = u'Обязательно должно быть заполнено хотя бы одно здание.'

        return error_string


def boiler_check(org):
    consum_flag = ConsumRes.objects.filter(org=org, resource__boiler_flag=True, checked=True).exclude(resource__alias='electro')
    if consum_flag:
        boilers = Boiler.objects.filter(org=org, is_delete=False)
        if not boilers:
            error_string = u'Обязательно должно быть заполнено хотя бы одна котельная'

            return error_string


def settlement_account_check(org):
    def maptest(x, y):
        if x and y:
            return int(x)*int(y)

    bik = org.bik
    settlement_account = org.settlement_account

    if len(bik) == 9 and len(settlement_account) == 20:
        if int(bik[6:9]) == 1 or int(bik[6:9]) == 0:
            bik_value = '0'+bik[4:6]
        else:
            bik_value = bik[6:9]

        coefficient_dict = [7, 1, 3] * 10

        control = 0

        for value in map(maptest,list(bik_value)+list(settlement_account),coefficient_dict):
            if value:
                control += int(str(value)[-1])

        if control % 10 != 0:
            error_string = u'Расчетный счет - проверка по контрольным сумма не пройдена'
            return error_string