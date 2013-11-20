#-*- coding: utf-8 -*-

u"""Команда выгрузки отчетов с набором параметров.
"""

from django.core.management.base import BaseCommand

from epm.models import EPassport, ExportTask, User, Contract
from filemanaging.models import EPMFile
from extui.views import build_common_forms, build_report, fix_media_slash
from extui.xml import show_html_form, show_pdf

import xhtml2pdf.pisa as pisa
import cStringIO as StringIO
from datetime import datetime
from time import time
import codecs
import os
import shutil
from django.core.mail import send_mail
from optparse import make_option

from PyPDF2 import PdfFileWriter, PdfFileReader


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--contract'),
        make_option('--id'),
        make_option('--passports'),

        make_option('--pdf'),
        make_option('--xml'),
        make_option('--pz'),
        make_option('--xls'),

        make_option('--folder'),
        make_option('--reload'),
    )

    def handle(self, *args, **options):
        passports = None
        now = str(datetime.now())

        #contracts_without_tvo = [contract for contract in Contract.objects.filter(name__contains='МК ', is_delete=False).exclude(name__contains='МК КК')]
        contracts_without_tvo = [contract for contract in Contract.objects.filter(name__contains='МК ', is_delete=False)]

        dropped = []
        pids = []
        lots = []
        result_msg = []
        export_passports = {}
        if not options['pdf'] and not options['xml'] and not options['pz'] and not options['xls']:
            options['pdf'] = True
            options['xml'] = True
            options['pz'] = True
            #options['xls'] = True

        if options['id']:
            passports = EPassport.objects.filter(pk=options['id'])
        if options['passports']:
            passport_ids = options['passports'].split(',')
            passports = EPassport.objects.filter(is_delete=False, pk__in=passport_ids)
        if options['contract']:
            passports = EPassport.objects.filter(is_delete=False, contract=options['contract'])


        if options['reload']:
            tasks = ExportTask.objects.filter(status__in=[2,3,5], is_delete=False).update(status=1)

        if passports:
            tasks = ExportTask.objects.filter(status=1, passport__in=passports, is_delete=False)
        else:
            tasks = ExportTask.objects.filter(status=1, is_delete=False)

        if tasks:
            for task in tasks:
                export_passports[task.id] = task.passport
                pids.append(str(task.passport_id))
                lots.append(str(task.passport.lot))
                task.status = 2
                task.save()





            for task_id, passport in export_passports.iteritems():

                task = ExportTask.objects.get(pk=task_id)
                task.status = 3
                task.save()

                if options['folder']:
                    directory = 'media/documents/public/export/%s/%s/%s/' % (options['folder'], passport.contract.name.strip(), passport.lot)
                else:
                    directory = 'media/documents/public/export/%s/%s/' % (passport.contract.name.strip(), passport.lot)
                try:
                    if not os.path.exists(directory):
                        os.makedirs(directory)
                except:
                    dropped.append({
                        passport.id: u'Ошибка создания каталога'
                    })

                passport.short_name = passport.short_name.strip()
                passport.save()

                if passport.short_name.find('/') >= 0:
                    passport_name = passport.short_name.replace('/', ' ')
                else:
                    passport_name = passport.short_name
                if passport_name.find('"') >= 0:
                    passport_name = passport_name.replace('"', '')

                start = time()

                if passport.contract in contracts_without_tvo:
                    options['xls'] = True

                xml_filename = u'%s%s_%s.xml' % (directory, passport.lot, passport_name)
                try:
                    xml = build_common_forms(passport.id)
                    result_msg.append(u'lot: %s - XML: %s' % (passport.lot, xml_filename))
                except Exception, e:
                    dropped.append({
                        passport.id: e
                    })
                    xml = None
                    task.status = 5
                    task.save()

                print u'%s =========>>>>>>build common forms >>> %s' % (passport.id, (time()-start))
                if xml:
                    if passport.contract.id == 10:
                        html = show_html_form(xml, 'common_template_interrao.xsl')
                    else:
                        html = show_html_form(xml, 'common_template_newform3.xsl')

                    if options['xml']:
                        xml_file = open(xml_filename, 'w')
                        xml_file.write(xml)
                        xml_file.close()

                        print u'%s =========>>>>>> save xml >>>> %s' % (passport.id, (time()-start))

                    if options['xls']:
                        excel_filename = u'%s%s_%s.xls' % (directory, passport.lot, passport_name)
                        css = open('media/css/excel.css').read()
                        excel = html.replace('<link rel="stylesheet" type="text/css" href="/media/css/pdf.css" />', '<style type="text/css">%s</style>' % css)
                        excel_file = open(excel_filename, 'w')
                        excel_file.write(excel)
                        excel_file.close()
                        result_msg.append(u'lot: %s - Excel: %s' % (passport.lot, excel_filename))

                    if options['pdf']:

                        html = show_pdf(html)

                        pdf_filename = u'%s%s_%s.pdf' % (directory, passport.lot, passport_name)
                        pdf_file = open(pdf_filename, 'w')
                        pisa.pisaDocument(StringIO.StringIO(html), pdf_file)
                        pdf_file.close()

                        result_msg.append(u'lot: %s - ЭП: %s' % (passport.lot, pdf_filename))

                        print u'%s =========>>>>>> %s' % (passport.id, (time()-start))

                    if options['pz']:
                        pz_filename = u'%s%s_ПЗ_%s.pdf' % (directory, passport.lot, passport_name)
                        try:
                            html = build_report(passport.id)
                        except Exception, e:
                            dropped.append({
                                passport.id: e
                            })
                            task.status = 5
                            task.save()
                            html = None
                        print u'%s =========>>>>>>build report >>> %s' % (passport.id, (time()-start))

                        if html:

                            temp_pz_file = open('temp_pz.pdf', 'w')
                            try:
                                pisa.pisaDocument(StringIO.StringIO(fix_media_slash(html)), temp_pz_file)
                            except Exception, e:
                                dropped.append({
                                    passport.id: e
                                })
                                task.status = 5
                                task.save()
                            temp_pz_file.close()

                            try:
                                report_file = PdfFileReader(open('temp_pz.pdf'))
                            except Exception, e:
                                dropped.append({
                                    passport.id: e
                                })
                                report_file = None

                            if report_file:
                                appended_report = PdfFileWriter()
                                for page in xrange(report_file.getNumPages()):
                                    appended_report.addPage(report_file.getPage(page))

                                result_msg.append(u'lot: %s - Отчет: %s' % (passport.lot, pz_filename))

                                print u'%s =========>>>>>> %s' % (passport.id, (time()-start))
                            else:
                                appended_report = None

                        else:
                            appended_report = None

                        if appended_report:


                            files = EPMFile.objects.filter(passport=passport, type__code='instrum_tvo_report', active=True)
                            for file in files:
                                if passport.contract not in contracts_without_tvo:
                                    if os.path.splitext(file.epmfile.path)[1] == '.pdf' or os.path.splitext(file.epmfile.path)[1] == '.PDF':
                                        tvo_file = PdfFileReader(open(file.epmfile.path))
                                        for page in xrange(tvo_file.getNumPages()):
                                            appended_report.addPage(tvo_file.getPage(page))
                                        result_msg.append(u'lot: %s - Добавлены ТВО в отчет: %s' % (passport.lot, file.name))
                                    else:
                                        try:
                                            shutil.copy2(file.epmfile.path, directory)
                                            result_msg.append(u'lot: %s - ТВО: %s' % (passport.lot, file.name))
                                        except Exception, e:
                                            dropped.append({
                                                passport.id: e
                                            })
                                            task.status = 5
                                            task.save()

                                else:
                                    try:
                                        shutil.copy2(file.epmfile.path, directory)
                                        result_msg.append(u'lot: %s - ТВО: %s' % (passport.lot, file.name))
                                    except Exception, e:
                                        dropped.append({
                                            passport.id: e
                                        })
                                        task.status = 5
                                        task.save()


                            appended_file = open(pz_filename, 'w')
                            appended_report.write(appended_file)
                            appended_file.close()





                    task.status = 4
                    task.save()
                    result_msg.append('')



        print '=================================== RESULT DROPPED ================================'
        print dropped
        print '======================================= END  ======================================'

        now = str(datetime.now())
        if result_msg:

            emails = []

            try:
                users = User.objects.filter(groups__name='file-access', is_active=True)
            except:
                users = None

            if users:
                for user in users:
                    if user.email not in emails:
                        emails.append(user.email)


#            emails.append('kashoutin.s@gmail.com')

            send_mail(
                u'Результат выгрузки ПЗ [%s]' % now,
                u'Объекты (номера по контракту): %s\nРезультат:\n%s\nОшибки:%s' % (','.join(lots),'\n'.join(result_msg).replace('media/documents/public/', ''), dropped),
                'epm2@project-service.ru',
                emails,
                fail_silently=False
            )
