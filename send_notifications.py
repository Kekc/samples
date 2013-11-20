def send_notification(alias='', recipients=[], msg='', document=None, docfile=None, comment=None):
    u"""Функция рассылки уведомлений по различным событиям: изменения статуса, обновление комментариев,
        загрузка файлов. Проверка настроек почтовых уведомлений пользователей. 
    """
    send_time = datetime.now()
    errors = []
    errors_dict = {
        'alias': alias,
        'recipients': [recipient.id for recipient in recipients if recipient],
        'msg': msg,
        'document': document.id if document else '',
        'docfile': docfile.id if docfile else '',
        'comment': comment.id if comment else '',
        'send_time': send_time,
        'description': '',
    }

    if document and document.org:
        if recipients:
            if alias:
                actual_recipients = []
                for recipient in recipients:
                    try:
                        mail_rules = recipient.mailrule_user_related
                    except:
                        mail_rules = None
                    if mail_rules and getattr(mail_rules, alias):
                        actual_recipients.append(recipient)
            else:
                actual_recipients = recipients

            rec_mails = [recipient.email for recipient in actual_recipients if recipient and recipient.email]

            if msg and msg in NOTIFICATION_MESSAGES:
                topic = u'Документоборот. %s' % NOTIFICATION_MESSAGES[msg]['topic']
                if NOTIFICATION_MESSAGES[msg]['variable'] == 'status':
                    variable = document.status.name
                elif NOTIFICATION_MESSAGES[msg]['variable'] == 'comment' and comment:
                    variable = u'%s: %s' % (comment.user.username, comment.text)
                elif NOTIFICATION_MESSAGES[msg]['variable'] == 'docfile' and docfile:
                    variable = u'%s: %s' % (docfile.file_type.name, docfile.name)
                else:
                    variable = None

                message = NOTIFICATION_MESSAGES[msg]['msg']
                if variable:
                    message %= variable

                message += u'\nНаименование объекта: %s' % document.org.name
                message += u'\nПросмотр: http://documents.fedes.ru'

                send_mail(topic, message, 'usermanager@fedes.ru', rec_mails, fail_silently=False)
                Notification(
                    topic=topic,
                    message=message,
                    recipients=rec_mails,
                ).save()

            else:
                msg_error = errors_dict.copy()
                msg_error['description'] = 'Message not found'
                errors.append(msg_error)

        else:
            recipients_error = errors_dict.copy()
            recipients_error['description'] = 'Recipients not found'
            errors.append(recipients_error)

    else:
        document_error = errors_dict.copy()
        document_error['description'] = 'Document not found'
        errors.append(document_error)

    if errors:
        err_topic = u'Документооборот. Ошибки рассылки'
        err_message = ' \n '.join([str(err_dict) for err_dict in errors])
        admin_mails = ['msitnikov@project-service.ru']
        send_mail(err_topic, err_message, 'usermanager@fedes.ru', admin_mails, fail_silently=False)