class JsonRpcData(object):
    u"""Обновление прав пользователей в различных приложениях
    """
    def __init__(self):

        self.service = ServiceProxy(settings.JSON_RPC_SERVICE_URL)
        self.application_access = False
        self.result = None
        self.usename = None

    def user_credentials(self, username):

        try:
            self.usename = username
            self.result = self.service.json_rpc.info(
                settings.JSON_RPC_SERVICE_USER,
                settings.JSON_RPC_SERVICE_PASS,
                username,
                settings.APPLICATION_ALIAS
            )
            if not self.result['error'] and 'result' in self.result:
                if self.result['result']:
                    if settings.APPLICATION_ALIAS in self.result['result']['applications']:
                        self.application_access = True
                    return self.result['result']
                else:
                    return None
            else:
                return None

        except IOError:
            return None

    def update_user(self):
        '''
        Обновление состояния групп пользователя
        '''
        if self.result:
          
            if self.usename:
                try:
                    user = User.objects.get(username=self.usename)
                except:
                    user = None
            else:
                user = None



            if user and self.result['result']['app_roles']:

                # очистка существущих групп
                user.groups.clear()


                for app_role in self.result['result']['app_roles']:
                    try:
                        group = Group.objects.get(name=app_role)
                    except Group.DoesNotExist:
                        group = Group(name=app_role)
                        group.save()

                    if group:
                        user.groups.add(group)